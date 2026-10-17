from pathlib import Path
import hashlib

path = Path("app/src/main/kotlin/com/metrolist/music/db/DatabaseDao.kt")
data = path.read_bytes()
expected_size = 77450
expected_sha = "6a2fd9bc600a38537ead7a6e1563c14bd3b9744d"
actual_sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
print(f"DatabaseDao size={len(data)} git_blob_sha={actual_sha}")
if len(data) != expected_size or actual_sha != expected_sha:
    raise SystemExit("DatabaseDao.kt does not match the audited upstream blob; refusing to patch")

text = data.decode("utf-8")
old = """            }.forEach(::upsert)

        albumPage.album.artists?.let { artists ->
            // Recreate album artists"""
new = """            }.forEach(::upsert)

        // A refreshed page replaces the tracklist: drop mappings for songs it no
        // longer lists, or entries cached during a partial release stay forever.
        // Only this album's mappings are touched; the songs themselves are kept.
        if (albumPage.songs.isNotEmpty()) {
            deleteStaleSongAlbumMaps(albumPage.album.browseId, albumPage.songs.map { it.id })
        }

        albumPage.album.artists?.let { artists ->
            // Recreate album artists"""
if text.count(old) != 1:
    raise SystemExit(f"update() patch anchor count is {text.count(old)}, expected 1")
text = text.replace(old, new)

anchor = """    @Update
    fun update(playlistEntity: PlaylistEntity, playlistItem: PlaylistItem) {"""
helper = """    @Query("DELETE FROM song_album_map WHERE albumId = :albumId AND songId NOT IN (:songIds)")
    fun deleteStaleSongAlbumMaps(
        albumId: String,
        songIds: List<String>,
    )

""" + anchor
if text.count(anchor) != 1:
    raise SystemExit(f"helper anchor count is {text.count(anchor)}, expected 1")
text = text.replace(anchor, helper)

if text.count("deleteStaleSongAlbumMaps") != 2:
    raise SystemExit("patched DatabaseDao does not contain exactly the helper declaration and call")
if "@Transaction\n    fun update(\n        album: AlbumEntity" not in text:
    raise SystemExit("album update transaction marker not found")

path.write_text(text)
print(f"patched lines={len(text.splitlines())}")
