import difflib
import numpy as np
import pandas as pd
import re
import string

from datetime import datetime
from jiwer import wer, cer
from math import ceil
from typing import List, Dict, Union, Tuple


# ============================== DATA MANIPULATION ==============================


def change_to_seconds(x: Union[str, None]) -> Union[int, None]:
    """
    Convert a time string in the format '%M:%S' to seconds.
    Args:
        x: The time string in the format '%M:%S'.
    Returns:
        x: The time in seconds or None if the input is NaN.
    """
    if pd.notna(x):
        time_obj = datetime.strptime(x, "%M:%S")
        x = int(time_obj.minute * 60 + time_obj.second)
    return x


def en_short_forms() -> Dict[str, str]:
    """
    Generate a dictionary mapping English short forms to their full forms.
    Returns:
        Dict[str, str]: A dictionary containing English short forms as keys
                        and their full forms as values.
    """
    pronouns = ["i", "you", "he", "she", "it", "we", "they", "who"]
    short_forms = ["'m", "'s", "'ll", "'ve", "'d"]
    full_forms = ["am", "is", "will", "have", "would"]

    all_forms = {}
    for pronoun in pronouns:
        for short_form, full_form in zip(short_forms, full_forms):
            s = f"{pronoun}{short_form}"
            f = f"{pronoun} {full_form}"
            all_forms[s] = f
    return all_forms


def remove_punctuation(text: str) -> str:
    """
    Remove punctuation from a given text.
    Args:
        text: The input text.
    Returns:
        str: The text with punctuation removed.
    """
    translator = str.maketrans("", "", string.punctuation)
    result_string = text.translate(translator)
    return result_string


def remove_words(text: str, words_to_remove: List[str]) -> str:
    """
    Remove specified words from the given text.
    Args:
        text: Input text.
        words_to_remove: List of words to be removed.
    Returns:
        str: Text with specified words removed.
    """
    filtered_words = [
        word for word in text.split() if word.lower() not in words_to_remove
    ]
    text = " ".join(filtered_words)
    return text


def replace_words(text: str, replacements: Dict[str, str]) -> str:
    """
    Replace words in the given text based on the provided replacements dictionary.
    Args:
        text: The input text.
        replacements: A dictionary mapping words to their replacements.
    Returns:
        str: The text with words replaced.
    """
    result_string = ""
    for word in text.split():
        if word.lower() in replacements:
            word = replacements[word.lower()]
        result_string += word + " "
    return result_string.strip()


def remove_consecutive_duplicates(text: str) -> str:
    """
    Remove consecutive duplicate words in the given text.
    Args:
        text: The input text.
    Returns:
        str: The text with consecutive duplicate words removed.
    """
    pattern = re.compile(r"\b(\w+)(?:\W+\1\b)+", re.IGNORECASE)
    return pattern.sub(r"\1", text)


def clean_text(
    text: str, replacements: Dict[str, str], to_remove: List[str], cased=True
) -> str:
    """
    Clean and preprocess the input text.
    Args:
        text: The input text.
        replacements: A dictionary mapping words to their replacements.
        to_remove: A dictionary mapping words to be removed.
        cased: If True, maintain the case; if False, convert to lowercase.
    Returns:
        str: The cleaned and preprocessed text.
    """

    text = text.replace("-", " ")
    text = replace_words(text, replacements)
    text = remove_punctuation(text)
    text = replace_words(text, replacements)
    text = remove_words(text, to_remove)
    text = remove_consecutive_duplicates(text)
    if not cased:
        text = text.lower()
    return text


def tokenize(text: str) -> list:
    """
    Tokenize the input text.
    Args:
        text: The input text.
    Returns:
        list: A list of tokens.
    """
    return re.split(r"\s+", text)


def untokenize(text_list: list) -> str:
    """
    Untokenize the list of tokens.
    Args:
        text_list: A list of tokens.
    Returns:
        str: The untokenized text.
    """
    return " ".join(text_list)


# ============================== STRINGS COMPARISON ==============================


def print_centered_columns(column_names: List[str], width: int) -> None:
    """
    Print a table with centered column names.
    Args:
        column_names: List of column names.
        width: Width of each column.
    """
    total_width = width * len(column_names) + (len(column_names) - 1)
    separator = "|"
    print(separator + "-" * (total_width + len(column_names)) + separator)

    for name in column_names:
        padding = (width - len(name)) // 2
        left_padding = padding
        right_padding = padding + (width - len(name)) % 2
        print(separator + " " * left_padding + name + " " * right_padding, end="")
    print("  " + separator)
    print(separator + "-" * (total_width + 2) + separator)


def print_to_width(text: str, width: int) -> None:
    """
    Print text with line breaks to fit the specified width.
    Args:
        text: The input text.
        width: The desired width.
    """
    length = len(text)
    num_of_lines = ceil(length / width)
    for i in range(num_of_lines):
        print(text[i * width : (i + 1) * width])
    print()


def equalize(s1: str, s2: str) -> Tuple[str, str]:
    """
    Equalize two strings for comparison.
    Parameters:
        s1: First string.
        s2: Second string.
    Returns:
        Tuple[str, str]: Equalized strings.
    """
    l1 = tokenize(s1)
    l2 = tokenize(s2)
    res1 = []
    res2 = []
    prev = difflib.Match(0, 0, 0)
    for match in difflib.SequenceMatcher(a=l1, b=l2).get_matching_blocks():
        if prev.a + prev.size != match.a:
            for i in range(prev.a + prev.size, match.a):
                res2 += ["_" * len(l1[i])]
            res1 += l1[prev.a + prev.size : match.a]
        if prev.b + prev.size != match.b:
            for i in range(prev.b + prev.size, match.b):
                res1 += ["_" * len(l2[i])]
            res2 += l2[prev.b + prev.size : match.b]
        res1 += l1[match.a : match.a + match.size]
        res2 += l2[match.b : match.b + match.size]
        prev = match
    return untokenize(res1), untokenize(res2)


def insert_newlines(string: str, every: int = 64, window: int = 10) -> List[str]:
    """
    Insert newlines in a string at specified intervals.
    Args:
        string: The input string.
        every: Insert newline every 'every' characters.
        window: Window size for finding a suitable break point.
    Returns:
        List[str]: List of strings with inserted newlines.
    """
    result = []
    from_string = string
    while len(from_string) > 0:
        cut_off = every
        if len(from_string) > every:
            while (from_string[cut_off - 1] != " ") and (cut_off > (every - window)):
                cut_off -= 1
        else:
            cut_off = len(from_string)
        part = from_string[:cut_off]
        result += [part]
        from_string = from_string[cut_off:]
    return result


def show_comparison(
    s1: str,
    s2: str,
    width: int = 40,
    margin: int = 10,
    sidebyside: bool = True,
    compact: bool = False,
) -> None:
    """
    Show a comparison between two strings.
    Args:
        s1: First string.
        s2: Second string.
        width: Width of the output.
        margin: Margin for side-by-side comparison.
        sidebyside: If True, display side-by-side comparison; 
                    otherwise, display vertically.
        compact: If True, display compact side-by-side comparison.
    """
    s1, s2 = equalize(s1, s2)

    if sidebyside:
        s1 = insert_newlines(s1, width, margin)
        s2 = insert_newlines(s2, width, margin)
        if compact:
            for i in range(0, len(s1)):
                lft = re.sub(" +", " ", s1[i].replace("_", "")).ljust(width)
                rgt = re.sub(" +", " ", s2[i].replace("_", "")).ljust(width)
                print(lft + " | " + rgt + " | ")
        else:
            for i in range(0, len(s1)):
                lft = s1[i].ljust(width)
                rgt = s2[i].ljust(width)
                print(lft + " | " + rgt + " | ")
    else:
        print(s1)
        print(s2)


def compare_words(reference: List[str], hypothesis: List[str]) -> Tuple[set, set, set]:
    """
    Compare words between two lists.
    Args:
        reference: Reference list of words.
        hypothesis: Hypothesis list of words.
    Returns:
        Tuple[set, set, set]: Common words, missing words, extra words.
    """
    common_words = set(reference) & set(hypothesis)
    missing_words = set(reference) - common_words
    extra_words = set(hypothesis) - common_words

    return common_words, missing_words, extra_words


# ============================== METRICS CALCULATION ==============================

from typing import List, Union
from jiwer import wer, cer


def calculate_wer(
    ground_true: str,
    hypothesis: str,
    replacements: dict,
    to_remove: list,
    cased: bool = True,
) -> float:
    """
    Calculate Word Error Rate (WER) between ground truth and hypothesis.
    Args:
        ground_true: The ground truth text.
        hypothesis: The hypothesis text.
        replacements: A dictionary mapping words to their replacements.
        to_remove: A list of words to be removed.
        cased: If True, maintain the case; if False, convert to lowercase.
    Returns:
        float: The WER value, rounded to 2 decimal places.
    """
    ground_true = clean_text(ground_true, replacements, to_remove, cased)
    hypothesis = clean_text(hypothesis, replacements, to_remove, cased)
    y_true = [ground_true]
    y_hat = [hypothesis]
    wer_value = wer(y_true, y_hat)
    return round(100 * wer_value, 2)


def calculate_cer(
    ground_true: str,
    hypothesis: str,
    replacements: dict,
    to_remove: list,
    cased: bool = True,
) -> float:
    """
    Calculate Character Error Rate (CER) between ground truth and hypothesis.
    Args:
        ground_true: The ground truth text.
        hypothesis: The hypothesis text.
        replacements: A dictionary mapping words to their replacements.
        to_remove: A list of words to be removed.
        cased: If True, maintain the case; if False, convert to lowercase.
    Returns:
        float: The CER value, rounded to 2 decimal places.
    """
    ground_true = clean_text(ground_true, replacements, to_remove, cased)
    hypothesis = clean_text(hypothesis, replacements, to_remove, cased)
    y_true = [ground_true]
    y_hat = [hypothesis]
    cer_value = cer(y_true, y_hat)
    return round(100 * cer_value, 2)


def weighted_wer(weights: List[int], wers: List[float]) -> float:
    """
    Calculate weighted average of Word Error Rates (WER).
    Args:
        weights: List of weights for each WER (number of words).
        wers: List of WER values.
    Returns:
        float: The weighted WER value, rounded to 2 decimal places.
    """
    wwer = sum(weight * wer for weight, wer in zip(weights, wers)) / sum(weights)
    return round(wwer, 2)
