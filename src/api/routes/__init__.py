"""
Routes package for STT API
Contains all route blueprints for the application
""" 
# from .transcription import transcription_bp
# from .translation import translation_bp
from .file import file_bp 
from .post_process import post_process_bp
__all__= ["file_bp", "post_process_bp"]