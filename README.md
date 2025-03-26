# Auroral Map Desktop Viewer

A real-time aurora visualization tool that displays the current auroral activity using data from NOAA's SWPC (Space Weather Prediction Center).

## Features

- Real-time auroral oval visualization
- OpenGL-based rendering for smooth performance
- Color-coded intensity display
- Interactive color key showing aurora intensity scale
- Global coverage with accurate geographic mapping

## Requirements

- Python 3.7+
- Required packages:
  - numpy
  - requests
  - Pillow
  - PyOpenGL

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install numpy requests Pillow PyOpenGL
```

## Usage

Run the main program:
```bash
python main.py
```

## Data Source

The program uses real-time aurora forecast data from:
https://services.swpc.noaa.gov/json/ovation_aurora_latest.json

## Color Interpretation

The visualization uses a green-blue gradient to represent aurora intensity:
- Lighter green: Lower aurora activity
- Brighter green with blue tint: Higher aurora activity
- The color key at the bottom shows the full intensity range

## Technical Details

- Resolution: 720x360 pixels
- Update frequency: Based on NOAA's data refresh rate
- Smoothing radius: 5 pixels
- Intensity scale: 150 (adjustable)

## License

MIT License
