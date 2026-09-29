# Destination photography

These images are cached Wikimedia Commons thumbnails. Source, author and license
links are stored in `../../data/destination-photos.json` and displayed in the
destination details dialog. The Home hero carries its own attribution.

- `destination-1.jpg`: Chowmahalla Palace 01, Bernard Gagnon, CC BY-SA 3.0.
- `destination-2.jpg`: Birla Mandir Hyderabad, Mayur Panchamia, CC BY-SA 4.0.
- `destination-3.jpg`: Osmania University Arts College 02, C. Chandra Kanth Rao,
  public domain.

Files are unmodified downloaded thumbnails. CSS crops their display to fit the
layout. New catalogue entries must identify the actual destination and include
verified author and license information. Unmatched destinations use a labeled
placeholder, never an unrelated photo.

Regenerate the catalogue and descriptions with
`python tools/build_destination_assets.py` from the project root. This command
downloads photos and reads the existing destination knowledge CSV; it does not
call an AI service or change the destination database.
