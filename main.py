import functions_framework # accessible to Google Cloud Functions
import spotipy
from pprint import pprint

from utils import (pitch_to_camelot, 
                    extract_playlist_id, 
                    reorder_list, 
                    convert_tracks_dict_to_list, 
                    create_new_playlist)

@functions_framework.http
def make_playlist(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.  Expects access_token and playlist_url query string parameters
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`.  We'll return the new playlist url here if successful.
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    Note:
        For more information on how Flask integrates with Cloud
        Functions, see the `Writing HTTP functions` page.
        <https://cloud.google.com/functions/docs/writing/http#http_frameworks>
    """

    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }

        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    request_json = request.get_json()

    if request_json and 'access_token' in request_json and 'playlist_url' in request_json:
    # TODO - add make_public option:
    #if request_json and 'access_token' in request_json and 'playlist_url' and 'make_public' in request_json:
        # Check that the playlist url is valid before proceeding
        PLAYLIST_URL = request_json['playlist_url']
        assert PLAYLIST_URL != "https://open.spotify.com/playlist/...", "Playlist URL is not valid!"

        # Create the Spotipy Client using Spotify access token
        try: 
            sp = spotipy.Spotify(auth=request_json['access_token'], requests_session=True, client_credentials_manager=None, 
                                        oauth_manager=None, auth_manager=None, proxies=None, 
                                        requests_timeout=5, status_forcelist=None, retries=2, 
                                        status_retries=1, backoff_factor=0.3, language=None)
        except Exception as e:
            print(f"An error occurred initializing the Spotipy client: {e}")

        # Create a dictionary that we'll use for storing track metadata
        tracks_dict = dict()
        # Get tracks from a given playlist ID.
        playlist_id = extract_playlist_id(PLAYLIST_URL)
        playlist_tracks = sp.playlist_tracks(playlist_id, limit=50)

        while playlist_tracks:
            for track_obj in playlist_tracks['items']:
                track = track_obj['track']
                tracks_dict[track['id']] = {
                    'artist': track['artists'][0]['name'],
                    'bpm': None,
                    'camelot': None,
                    'key': None,
                    'key_tonal': None,
                    'mode': None,
                    'name': track['name'],
                    'uri': track['uri']
                }

            if playlist_tracks['next']:
                playlist_tracks = sp.next(playlist_tracks)
            else:
                playlist_tracks = None

        num_tracks = len(tracks_dict)
        if num_tracks == 0:
            print("Error! No tracks found.")
            exit()
        
        # In case tracks_dict contains more than 100 tracks, we need to query for audio features in chunks 
        # Divide the track ids into chunks of max_track_ids, creating a list of lists of the track ids
        max_track_ids = 100
        track_ids_chunks = [list(tracks_dict.keys())[i:i+max_track_ids] for i in range(0, num_tracks, max_track_ids)]

        # Fetch audio features for each track in the chunk
        for chunk in track_ids_chunks:
            tracks_meta = sp.audio_features(chunk)

            for track_meta_obj in tracks_meta:
                track_id = track_meta_obj['id']
                tracks_dict[track_id].update({
                    'bpm': track_meta_obj['tempo'],
                    'key': track_meta_obj['key'],
                    'mode': track_meta_obj['mode'],
                })

                # Use the pitch_to_camelot() function to get additional data for each track
                camelot, key_tonal = pitch_to_camelot(track_meta_obj['key'], track_meta_obj['mode'])
                tracks_dict[track_id].update({
                    'camelot': camelot,
                    'key_tonal': key_tonal,
                })

        # TODO - this simply changes the schema from a dictionary to a list of objects, we could create it as such to begin with above
        new_list = []
        for key, value in tracks_dict.items():
            new_dict = value.copy()
            new_dict["id"] = key
            new_list.append(new_dict)

        # Assess the similarity between all tracks and then reorder the list
        sorted_tracks_list = reorder_list(unsorted_tracks_list)

        # Create a list containing just the track URIs
        sorted_track_uris_list = []
        for track in sorted_tracks_list:
            sorted_track_uris_list.append(track['uri'])
        # pprint("# of items to be added to new playlist: " + str(len(track_uris_list)))

        # Experiment - reverse order for energizing style?
        sorted_track_uris_list.reverse()

        def create_new_playlist():
            # Get the current user id (inherited from access token)
            user = sp.current_user()['id']

            # Get the current playlist name and description
            # Note, the API returns fields in alphabetical order, not according to the order of fields passed as arguments
            playlist_desc, playlist_name = sp.playlist(playlist_id, fields="description,name").values()

            # TODO - check if the new playlist name is > 100 chars, decide what to do if it is
            new_playlist_name = f"{playlist_name} (sorted by Better Playlists)"

            # Create a new playlist
            new_playlist_id = sp.user_playlist_create(
                user, 
                new_playlist_name, 
                public=True, # TODO - public=request_json['make_public'] 
                collaborative=False, 
                description=playlist_desc
            )['id']

            # Add the tracks to the new playlist in batches of 100
            max_size = 100
            split_uris = [track_uris_list[i:i+max_size] for i in range(0, len(track_uris_list), max_size)]
            for uris in split_uris:
                sp.playlist_add_items(new_playlist_id, uris)

            return new_playlist_id


        new_playlist_id = create_new_playlist()
        new_playlist_url = f"https://open.spotify.com/playlist/{new_playlist_id}"
        new_playlist_deeplink = f"spotify://playlist/{new_playlist_id}"
        print(f"New playlist URL is {new_playlist_url}")
        
        response_dict = {
            "message": "Success", 
            "sorted_playlist": new_playlist_deeplink 
        }

        return (response_dict, 200, headers)
    else:
        return ({'message': "Error: access_token or playlist_url missing from request json"}, 404, headers)

