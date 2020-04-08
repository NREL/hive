LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': "[%(levelname)s] - %(name)s - %(message)s",
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        }
    }
}
