
# DAQ hardware
FS = 1000   # accelerometer sample rate (Hz)

CLASS_NAMES: list[str] = ["Healthy", "Degraded", "Damaged"]

# Label string → integer index (matches classifier module's health_label values)
LABEL_TO_INT: dict[str, int] = {name: i for i, name in enumerate(CLASS_NAMES)}
