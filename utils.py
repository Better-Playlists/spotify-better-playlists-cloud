def extract_playlist_id(url):
    """
    Extracts the playlist ID from a Spotify playlist URL.

    Args:
        url (str): The URL of the Spotify playlist.

    Returns:
        str: The ID of the playlist.
    """
    if '?' in url:
        playlist_id = url.split("/playlist/")[1].split("?")[0]
    else:
        playlist_id = url.split("/playlist/")[1]
    return playlist_id

# Create a dictionary that maps the Pitch Class notation (PCN) and mode (major/minor) of a note to its corresponding Camelot Wheel representation.
# The keys of the dictionary are tuples containing the PCN (0-11) and mode (0 for minor and 1 for major), and the values are tuples containing
# the Camelot Wheel code (1A-12B) and the letter of the corresponding musical key (A or B).
cw_map = {
    (0,1):(8,'B'),
    (1,1):(3,'B'),
    (2,1):(10,'B'),
    (3,1):(5,'B'),
    (4,1):(12,'B'),
    (5,1):(7,'B'),
    (6,1):(2,'B'),
    (7,1):(9,'B'),
    (8,1):(4,'B'),
    (9,1):(11,'B'),
    (10,1):(6,'B'),
    (11,1):(1,'B'),
    (0,0):(5,'A'),
    (1,0):(12,'A'),
    (2,0):(7,'A'),
    (3,0):(2,'A'),
    (4,0):(9,'A'),
    (5,0):(4,'A'),
    (6,0):(11,'A'),
    (7,0):(6,'A'),
    (8,0):(1,'A'),
    (9,0):(8,'A'),
    (10,0):(3,'A'),
    (11,0):(10,'A')
}

# Create a dictionary that maps the Pitch Class notation (PCN) to its corresponding musical key.
pitch_class_dict = {
    0: "C",
    1: "C♯/D♭",
    2: "D",
    3: "D♯/E♭",
    4: "E",
    5: "F",
    6: "F♯/G♭",
    7: "G",
    8: "G♯/A♭",
    9: "A",
    10: "A♯/B♭",
    11: "B"
}

# Helper dictionary for mapping Spotify mode value to major/minor string
major_minor_dict = {
    0: "minor",
    1: "major"
}

# This method takes a Pitch Class notation (PCN) and a mode (0 for minor, 1 for major), and returns a tuple containing the corresponding Camelot Wheel
# representation (1A-12B) and the tonal representation of the note (e.g. "C major").
def pitch_to_camelot(pcn, major):
    # Return the corresponding tonal representation of the input note
    tonal = pitch_class_dict[pcn] + " " + major_minor_dict[major]
    
    # Return the corresponding Camelot Wheel representation of the input note
    camelot = cw_map[pcn,major]
    
    return camelot, tonal

# Generate similarity scores for each track pairing
# ["camelot"][0] == the number 1-12, ["camelot"][1] == the letter "A" or "B"
def similarity_score(track1, track2):
    if track1["camelot"][0] == track2["camelot"][0] and track1["camelot"][1] == track2["camelot"][1]:
        return 6
    elif track1["camelot"][0] == track2["camelot"][0]:
        return 5 if track1["camelot"][1] == track2["camelot"][1] else 4 if abs(ord(track1["camelot"][1]) - ord(track2["camelot"][1])) == 1 else 1
    elif track1["camelot"][1] == track2["camelot"][1] and (track1["camelot"][0] - track2["camelot"][0] == 1 or track2["camelot"][0] - track1["camelot"][0] == 11):
        return 3
    elif track1["camelot"][1] == track2["camelot"][1] and (track1["camelot"][0] - track2["camelot"][0] == -1 or track2["camelot"][0] - track1["camelot"][0] == 11):
        return 3
    elif track1["camelot"][1] == track2["camelot"][1]:
        return 2 if abs(track1["camelot"][0] - track2["camelot"][0]) == 2 else 0
    else:
        return 0

# Track reordering algorithm
def reorder_list(lst):
    list_length = len(lst)
    score_matrix = [[similarity_score(lst[i], lst[j]) for j in range(list_length)] for i in range(list_length)]
    ordered_indices = [0]
    for i in range(list_length - 1):
        current_idx = ordered_indices[-1]
        max_score = -1
        max_idx = -1
        for j in range(list_length):
            if j not in ordered_indices:
                score = score_matrix[current_idx][j]
                if score > max_score:
                    max_score = score
                    max_idx = j
        ordered_indices.append(max_idx)
    return [lst[i] for i in ordered_indices]