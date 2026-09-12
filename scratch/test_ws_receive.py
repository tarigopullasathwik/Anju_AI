import inspect
import simple_websocket

def check_receive_signature():
    print("Checking simple-websocket receive signature...")
    try:
        # Get signature of Server.receive or inspect class methods
        server_class = simple_websocket.Server
        receive_method = server_class.receive
        sig = inspect.signature(receive_method)
        print(f"Server.receive signature: {sig}")
    except Exception as e:
        print(f"Error checking signature: {e}")

if __name__ == "__main__":
    check_receive_signature()
