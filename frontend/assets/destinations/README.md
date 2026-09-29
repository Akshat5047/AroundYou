# Destination photography

These images are locally cached Wikimedia Commons thumbnails. Source, author
and license links are stored in `../../data/destination-photos.json` and
displayed in the destination details dialog. Cards do not display a credit
footer. The Home hero carries its own attribution.

- `destination-1.jpg`: Chowmahalla Palace 01, Bernard Gagnon, CC BY-SA 3.0.
- `destination-2.jpg`: Birla Mandir Hyderabad, Mayur Panchamia, CC BY-SA 4.0.
- `destination-3.jpg`: Osmania University Arts College 02, C. Chandra Kanth Rao,
  public domain.

Files are unmodified downloaded thumbnails. CSS crops their display to fit the
layout. New catalogue entries must identify the actual destination and include
verified author and license information. Unmatched destinations keep a compact
card without a photo; unrelated locations, logos, generic wildlife photos and
unverified matches must not be substituted.

Regenerate the catalogue and descriptions with
`python tools/build_destination_assets.py` from the project root. This command
downloads photos and reads the existing destination knowledge CSV; it does not
call an AI service or change the destination database.

The expanded catalogue is preserved by that command. `place-*.jpg` files are
matched by destination name and district, with individual sources and licenses
in the JSON manifest. Some downloaded thumbnails are PNG data; browsers detect
the content format independently of the local extension.

After any catalogue change, run `python tools/bundle_destination_media.py` to
update the metadata embedded in the card script. This supports direct-file
previews and avoids JSON requests delaying photos. Run
`python tools/check_destination_photos.py` to validate every local image and
desktop/mobile layouts.

Candidate discovery tools are `tools/expand_destination_photos.py` and
`tools/discover_wikipedia_photos.py`. Candidates are not published automatically:
review their exact location, subject, author and license before marking them
approved in `.ui-preview/photo-candidates.json` and using `--download`.
