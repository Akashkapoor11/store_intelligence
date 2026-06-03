"""
main.py  —  Detection Pipeline Entry Point
──────────────────────────────────────────
Processes all 5 CCTV MP4 files (or live streams), runs YOLOv8 + ByteTrack,
maps detections to store zones, and emits structured events to the database.

Usage:
  python main.py                  # process all cameras from CCTV_PATH
  python main.py --cam "CAM 3"    # process single camera
"""

import os
import sys
import cv2
import time
import argparse
import threading
import sqlalchemy as sa
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger
from ultralytics import YOLO

from camera_config import CAMERA_CONFIGS, CameraConfig
from tracker import ByteTracker, Track
from zone_mapper import ZoneMapper
from staff_filter import StaffFilter
from reentry_guard import ReentryGuard
from event_emitter import EventEmitter
from db import get_engine

# ── Logging ──────────────────────────────────────────────────────────────────
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))
logger.add("/logs/detection_{time}.log", rotation="100 MB", retention="7 days")


class CameraProcessor:
    """Processes a single camera feed end-to-end."""

    def __init__(
        self,
        cam_config: CameraConfig,
        model: YOLO,
        emitter: EventEmitter,
        video_path: str,
        video_start_time: Optional[datetime] = None,
        process_every_n_frames: int = 3,   # process every 3rd frame for speed
    ):
        self.cfg      = cam_config
        self.model    = model
        self.emitter  = emitter
        self.video    = video_path
        self.start_ts = video_start_time or datetime(2026, 4, 10, 12, 0, 0)
        self.skip     = process_every_n_frames

        self.tracker  = ByteTracker(model)
        self.zone_map = ZoneMapper(cam_config)
        self.staff    = StaffFilter()
        self.reentry  = ReentryGuard()

        # State tracking
        self._person_zone: Dict[int, str]               = {}
        self._zone_enter_ts: Dict[int, datetime]        = {}
        self._entered_store: set                        = set()
        self._prev_cy: Dict[int, float]                 = {}
        self._exited_store: set                         = set()
        self._track_enter_ts: Dict[int, datetime]       = {}

    def process(self):
        cap = cv2.VideoCapture(self.video)
        if not cap.isOpened():
            logger.error(f"[{self.cfg.name}] Cannot open video: {self.video}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.staff.fps = fps
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_num = 0

        logger.info(
            f"[{self.cfg.name}] Starting: {self.video} | "
            f"{total_frames} frames @ {fps:.1f}fps"
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_num += 1
            if frame_num % self.skip != 0:
                continue

            h, w = frame.shape[:2]
            elapsed_sec = frame_num / fps
            frame_ts = self.start_ts + timedelta(seconds=elapsed_sec)

            # Run tracking
            tracks = self.tracker.update(frame, frame_num)

            # Update staff filter
            active_ids = {t.track_id for t in tracks if t.is_confirmed}
            self.staff.update(active_ids)

            for track in tracks:
                if not track.is_confirmed:
                    continue

                tid   = track.track_id
                pid   = f"{self.cfg.name.replace(' ', '')}_T{tid:04d}"
                is_st = self.staff.is_staff(tid)

                cx_frac = ((track.bbox[0] + track.bbox[2]) / 2) / w
                cy_frac = track.bbox[3] / h   # feet y

                # ── Entry / Exit detection (only on CAM 3) ──────────────────
                if self.cfg.is_entry_exit:
                    prev_cy = self._prev_cy.get(tid)

                    if self.zone_map.is_crossing_entry_line(prev_cy, cy_frac, "enter"):
                        if not is_st:
                            is_re = self.reentry.is_reentry(tid, cx_frac, cy_frac, frame_ts)
                            if not is_re and tid not in self._entered_store:
                                self._entered_store.add(tid)
                                self._track_enter_ts[tid] = frame_ts
                                self.emitter.emit(
                                    "entry", pid, frame_ts,
                                    camera_id=self.cfg.name,
                                    zone="entrance",
                                    is_staff=False,
                                    confidence=track.confidence,
                                    bbox=track.bbox,
                                    store_id=os.getenv("STORE_ID", "ST1076"),
                                )

                    if self.zone_map.is_crossing_entry_line(prev_cy, cy_frac, "exit"):
                        if tid in self._entered_store and tid not in self._exited_store:
                            self._exited_store.add(tid)
                            self.reentry.record_exit(tid, cx_frac, cy_frac, frame_ts)
                            enter_ts = self._track_enter_ts.get(tid, frame_ts)
                            dwell = (frame_ts - enter_ts).total_seconds()
                            self.emitter.emit(
                                "exit", pid, frame_ts,
                                camera_id=self.cfg.name,
                                zone="entrance",
                                dwell_seconds=dwell,
                                is_staff=False,
                                confidence=track.confidence,
                                bbox=track.bbox,
                                store_id=os.getenv("STORE_ID", "ST1076"),
                            )

                    self._prev_cy[tid] = cy_frac

                # ── Zone transition tracking (all cameras) ───────────────────
                current_zone = self.zone_map.get_zone(track.bbox, w, h)
                prev_zone    = self._person_zone.get(tid)

                if is_st:
                    continue  # skip zone events for staff

                if prev_zone is None:
                    # First time seeing this track
                    self._person_zone[tid]   = current_zone
                    self._zone_enter_ts[tid] = frame_ts
                    self.emitter.emit(
                        "zone_entered", pid, frame_ts,
                        camera_id=self.cfg.name,
                        zone=current_zone,
                        confidence=track.confidence,
                        bbox=track.bbox,
                        store_id=os.getenv("STORE_ID", "ST1076"),
                    )

                elif current_zone != prev_zone:
                    # Zone transition
                    enter_ts = self._zone_enter_ts.get(tid, frame_ts)
                    dwell    = (frame_ts - enter_ts).total_seconds()

                    self.emitter.emit(
                        "zone_exited", pid, frame_ts,
                        camera_id=self.cfg.name,
                        zone=prev_zone,
                        dwell_seconds=dwell,
                        confidence=track.confidence,
                        bbox=track.bbox,
                        store_id=os.getenv("STORE_ID", "ST1076"),
                    )
                    self.emitter.emit(
                        "zone_entered", pid, frame_ts,
                        camera_id=self.cfg.name,
                        zone=current_zone,
                        confidence=track.confidence,
                        bbox=track.bbox,
                        store_id=os.getenv("STORE_ID", "ST1076"),
                    )

                    self._person_zone[tid]   = current_zone
                    self._zone_enter_ts[tid] = frame_ts

            if frame_num % (int(fps) * 30) == 0:
                logger.info(
                    f"[{self.cfg.name}] Progress: {frame_num}/{total_frames} "
                    f"({100*frame_num/total_frames:.1f}%) "
                    f"time={frame_ts.strftime('%H:%M:%S')}"
                )

        cap.release()
        logger.info(f"[{self.cfg.name}] ✅ Processing complete.")

    # ── Staff events flush ───────────────────────────────────────────────────
    def flush_staff_events(self):
        for tid in self.staff.get_staff_ids():
            pid = f"{self.cfg.name.replace(' ', '')}_T{tid:04d}"
            self.emitter.emit(
                "staff_detected", pid, datetime.now(),
                camera_id=self.cfg.name,
                is_staff=True,
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cam", type=str, default=None, help="Process only this camera (e.g. 'CAM 3')")
    parser.add_argument("--threads", type=int, default=2, help="Parallel camera threads")
    args = parser.parse_args()

    cctv_path = os.getenv("CCTV_PATH", "/data/cctv")
    model_name = os.getenv("MODEL_NAME", "yolov8n.pt")

    logger.info("=" * 60)
    logger.info("Purplle Store Intelligence — Detection Pipeline")
    logger.info("=" * 60)

    # Wait for DB
    engine = get_engine()
    for attempt in range(30):
        try:
            with engine.connect() as c:
                c.execute(sa.text("SELECT 1"))
            logger.info("Database connection established ✓")
            break
        except Exception:
            logger.warning(f"Waiting for DB... ({attempt+1}/30)")
            time.sleep(2)

    emitter = EventEmitter()
    model   = YOLO(model_name)

    # Determine which cameras to process
    cams_to_process = (
        {args.cam: CAMERA_CONFIGS[args.cam]}
        if args.cam and args.cam in CAMERA_CONFIGS
        else CAMERA_CONFIGS
    )

    processors = []
    for cam_name, cam_cfg in cams_to_process.items():
        # Try direct config path first (handles 'Store 1/CAM 1.mp4' correctly)
        video_file = Path(cctv_path) / cam_cfg.filename
        
        # Fallbacks for flatter directory structures
        if not video_file.exists():
            video_file = Path(cctv_path) / cam_cfg.filename.split("/")[-1]
        if not video_file.exists():
            video_file = Path(cctv_path) / "CCTV Footage" / cam_cfg.filename.split("/")[-1]
            
        if not video_file.exists():
            logger.warning(f"[{cam_name}] Video not found: {video_file} (looked in multiple locations)")
            continue

        proc = CameraProcessor(
            cam_config=cam_cfg,
            model=model,
            emitter=emitter,
            video_path=str(video_file),
            # Metadata: video starts at store open (approx 12:00 based on CSV earliest order)
            video_start_time=datetime(2026, 4, 10, 12, 0, 0),
        )
        processors.append(proc)

    if not processors:
        logger.error("No valid camera files found. Check CCTV_PATH.")
        sys.exit(1)

    logger.info(f"Processing {len(processors)} camera(s) with {args.threads} thread(s)")

    # Run cameras in parallel threads (limited by args.threads)
    sem = threading.Semaphore(args.threads)

    def run_processor(p):
        with sem:
            try:
                p.process()
                p.flush_staff_events()
            except Exception as e:
                logger.error(f"[{p.cfg.name}] Error: {e}", exc_info=True)

    threads = [threading.Thread(target=run_processor, args=(p,)) for p in processors]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    logger.info("=" * 60)
    logger.info("✅ All cameras processed. Events written to database.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
