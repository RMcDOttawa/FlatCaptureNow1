class Constants:
    UNSAVED_WINDOW_TITLE = "(Unsaved Document)"
    SAVED_FILE_EXTENSION = ".ewho3"
    RESET_FONT_SIZE = 12
    MAIN_TITLE_LABEL_PREFIX = "MainTitle_"
    SUBTITLE_LABEL_PREFIX = "Subtitle_"
    MAIN_TITLE_FONT_SIZE_INCREMENT = 6
    SUBTITLE_FONT_SIZE_INCREMENT = 3
    SESSION_CONSOLE_INDENTATION_DEPTH = 3
    DELAY_AT_FINISH = 2  # Wait these seconds at end for output to appear on UI
    CANCELLABLE_WAIT_INCREMENTS = 0.5  # Wait in this many-second increments
    CAMERA_RESYNCH_TIMEOUT = 120  # Two minutes wait for camera to catch up should be plenty
    CAMERA_RESYNCH_CHECK_INTERVAL = 0.5  # Check if camera is done this often
    MAX_FRAMES_REJECTED_IN_A_ROW = 10
    LOCAL_PATH_NOT_SET = "(not set)"
    SLEW_DONE_POLLING_INTERVAL = 0.5    # Check if slew done at this frequency (seconds)
    SLEW_MAXIMUM_WAIT = 3 * 60      # Don't wait any longer than this for a slew
