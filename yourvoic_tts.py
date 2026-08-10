import os

def generate_speech(text: str, output_path: str = "computer_speech.wav") -> str:
    """
    Generates spoken Sanskrit audio from text using Vagdhenu TTS engine.
    """
    if not text or not text.strip():
        print("Empty text provided for TTS.")
        return ""

    try:
        # Import Vagdhenu engine dynamically from local module
        from vagdhenu import VagdhenuTTS
        
        engine = VagdhenuTTS()
        engine.synthesize(text=text.strip(), output_file=output_path)
        return output_path

    except ImportError:
        print("Vagdhenu module not found in environment. Please clone prathoshap/vagdhenu into your project.")
        return ""
    except Exception as e:
        print(f"Error generating speech with Vagdhenu: {e}")
        return ""
