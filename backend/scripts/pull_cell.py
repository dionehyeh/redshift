"""Script to pre-fetch and cache 20-year climatological normals for a target cell."""
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Pull and cache climatological cell normals")
    parser.add_argument("--lat", type=float, default=9.50, help="Latitude")
    parser.add_argument("--lon", type=float, default=76.40, help="Longitude")
    args = parser.parse_args()

    cell_id = f"{args.lat:04.1f}N_{args.lon:05.1f}E"
    print(f"Pre-caching cell {cell_id}...")
    print("In DEMO_MODE, built-in regional normals will be used.")

if __name__ == "__main__":
    main()
