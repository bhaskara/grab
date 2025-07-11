from typing import Set
import os


class Grab(object):
    """This class implements the logic of the grab game.

    """
    pass



def load_word_list(dict_name : str) -> Set[str]:
    """Loads a word list into a set of strings

    dict_name can be one of 'twl06' or 'sowpods'

    """
    # The word lists are in the data/ subdirectory of the repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    data_dir = os.path.join(repo_root, 'data')
    
    if dict_name not in ['twl06', 'sowpods']:
        raise ValueError(f"Unknown dictionary name: {dict_name}. Must be 'twl06' or 'sowpods'")
    
    dict_file = os.path.join(data_dir, f'{dict_name}.txt')
    
    if not os.path.exists(dict_file):
        raise FileNotFoundError(f"Dictionary file not found: {dict_file}")
    
    words = set()
    with open(dict_file, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip().lower()
            if word:  # Skip empty lines
                words.add(word)
    
    return words
    
