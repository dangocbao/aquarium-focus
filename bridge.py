"""
SeeTrue & EmotiBit → Browser bridge
===================================
Reads gaze from SeeTrue's ZMQ stream (port 3428) and heart rate from
EmotiBit's ZMQ stream (port 3429). Forwards normalized (0-1) coords
and heart rate to the browser over WebSocket.

SETUP (one time)
----------------
    pip install pyzmq websockets

TEST WITHOUT HARDWARE (do this first!)
--------------------------------------
Terminal 1:  python emotibit_simulator.py
Terminal 2:  cd seetrue_hackathon/python/gaze_data_simulator
             python simulator.py
Terminal 3:  python bridge.py
Then open your aquarium HTML — the red marker should move and waves should roll.

WITH REAL HARDWARE
------------------
Terminal 1:  start the SeeTrue recording app (pushes to port 3428)
Terminal 2:  start the EmotiBit data stream (pushes to port 3429)
Terminal 3:  python bridge.py
Then open your aquarium HTML.
"""

import asyncio
import json
import zmq
import zmq.asyncio
import websockets

# -------------------- CONFIG --------------------
ZMQ_EYE_PORT = "tcp://127.0.0.1:3428"   # where SeeTrue pushes gaze data
ZMQ_HR_PORT  = "tcp://127.0.0.1:3429"   # where EmotiBit pushes heart rate data
WS_HOST      = "localhost"
WS_PORT      = 8765
# ------------------------------------------------

# Latest data payload. Starts at center with an average resting heart rate.
latest_data = {"nx": 0.5, "ny": 0.5, "heart_rate": 75.0}


async def eye_reader():
    """Continuously read SeeTrue gaze and update latest_data."""
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.PULL)
    sock.setsockopt(zmq.RCVHWM, 0)
    sock.connect(ZMQ_EYE_PORT)
    print(f"✓ Listening for SeeTrue Gaze on {ZMQ_EYE_PORT}")

    while True:
        text = await sock.recv_string()
        fields = text.split(";")
        try:
            # Skip samples where eyes aren't detected
            event = fields[20].strip() if len(fields) > 20 else ""
            if event == "NA":
                continue

            nx = float(fields[2])   # GazeX, 0.0–1.0
            ny = float(fields[3])   # GazeY, 0.0–1.0

            # Skip (0, 0) — happens before tracking warms up
            if nx == 0.0 and ny == 0.0:
                continue

            latest_data["nx"] = nx
            latest_data["ny"] = ny
        except (ValueError, IndexError):
            pass   # malformed line — just wait for the next one


async def hr_reader():
    """Continuously read EmotiBit heart rate and update latest_data."""
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.PULL)
    sock.setsockopt(zmq.RCVHWM, 0)
    sock.connect(ZMQ_HR_PORT)
    print(f"✓ Listening for EmotiBit Heart Rate on {ZMQ_HR_PORT}")

    while True:
        text = await sock.recv_string()
        parts = text.split(";")
        
        # Expected format from simulator/device: "HR;85.5"
        if len(parts) == 2 and parts[0] == "HR":
            try:
                latest_data["heart_rate"] = float(parts[1])
            except ValueError:
                pass


async def ws_handler(websocket):
    """Send latest data to the browser ~60 times per second."""
    print("✓ Browser connected")
    try:
        while True:
            await websocket.send(json.dumps(latest_data))
            await asyncio.sleep(1 / 60)
    except websockets.exceptions.ConnectionClosed:
        print("✗ Browser disconnected")


async def main():
    print(f"✓ Bridge running on ws://{WS_HOST}:{WS_PORT}")
    
    # Run both ZMQ readers forever in the background
    asyncio.create_task(eye_reader())
    asyncio.create_task(hr_reader())
    
    # Serve the WebSocket for the browser
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        await asyncio.Future()   # run forever


if __name__ == "__main__":
    asyncio.run(main())