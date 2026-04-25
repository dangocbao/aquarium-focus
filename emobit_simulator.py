# emotibit_simulator.py
import zmq
import time
import math

def run_emotibit_simulator():
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    # Phát tín hiệu lên cổng 3429
    sock.bind("tcp://127.0.0.1:3429")
    print("💓 EmotiBit Simulator is running on port 3429...")

    base_hr = 75.0
    while True:
        # Tạo nhịp tim biến động (sóng sin + nhiễu ngẫu nhiên) để test độ cuộn của sóng biển
        current_hr = base_hr + math.sin(time.time() * 0.5) * 20 + math.cos(time.time() * 0.1) * 15
        
        # Format gửi đi: "HR;giá_trị" (VD: "HR;85.42")
        message = f"HR;{current_hr:.2f}"
        
        try:
            sock.send_string(message, zmq.NOBLOCK)
        except zmq.Again:
            pass
        
        time.sleep(0.1) # Gửi 10 lần/giây (10Hz)

if __name__ == "__main__":
    try:
        run_emotibit_simulator()
    except KeyboardInterrupt:
        print("\n🛑 Stop EmotiBit Simulator.")