import os
import webbrowser


def launch_streamlit_gui():
    """Launches the new Streamlit-based GUI for the Product Manager."""
    try:
        webbrowser.open("http://localhost:8501")
        os.system("streamlit run app.py")
    except KeyboardInterrupt:
        print("\nExiting GUI...")
    except Exception as e:
        print(f"Error launching GUI: {e}")


if __name__ == "__main__":
    launch_streamlit_gui()
