```tree
ai-instance-manager/
│
├── main.py                                 # FastAPI app entry point, route registration
├── requirements.txt                        # All dependencies
├── .env                                    # Environment variables (DISPLAY, MongoDB URL, etc.)
├── .gitignore                              # Git ignore file
├── README.md                               # This readme file
├── run.sh                                  # Run the FastAPI app with uvicorn
├── roadmap.md                              # Project roadmap
├── ai_instance_manager.code-workspace      # VS Code workspace file
├── setup_and_run.md                       # Installation and run instructions
│
├── app/
│   ├── config.py                           # App settings, env variables
│   ├── logging_service.py                  # MongoDB logging utility (used by all endpoints)
│   └── database.py                         # MongoDB connection
│
├── routes/
│   ├── mouse.py                            # Mouse position, move, click endpoints
│   ├── keyboard.py                         # Keyboard input endpoints
│   ├── screen.py                           # Screenshot + screen dimensions endpoints
│   ├── vision.py                           # YOLO detection + classification endpoints
│   └── health.py                           # Health check endpoint
│
├── services/
│   ├── mouse_service.py                    # PyAutoGUI mouse logic
│   ├── keyboard_service.py                 # PyAutoGUI keyboard logic
│   ├── screen_service.py                   # Screenshot logic
│   └── vision_service.py                   # YOLO integration logic
│
├── models/
│   ├── mouse_models.py                     # Pydantic request/response models for mouse
│   ├── keyboard_models.py                  # Pydantic models for keyboard
│   └── event_log_model.py                  # MongoDB event log schema
│
├── utils/
│   └── helpers.py                          # Helper functions, e.g., logging
│
└── tests/
    ├── test_mouse.py                       # Unit tests for mouse endpoints
    ├── test_keyboard.py                    # Unit tests for keyboard endpoints
    ├── test_screen.py                      # Unit tests for screen endpoints
    └── test_vision.py                      # Unit tests for vision endpoints

```
