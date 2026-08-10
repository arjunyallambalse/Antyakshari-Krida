import os

def generate_speech(text: str, output_path: str = "computer_speech.wav") -> str:
    """
  
    """
    if not text or not text.strip():
        print("Empty text provided for TTS.")
        return ""

    try:
        # Import Vagdhenu e
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
