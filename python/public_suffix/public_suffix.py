"""
Domain Name Validation and Public Suffix List (PSL) Analyzer

This script provides domain name validation and analysis using the Public
Suffix List (PSL). It can validate domain names according to RFC standards
and extract Top-Level Domain (TLD) and Second-Level Domain (SLD) information.

Features:
    - Domain name format validation using regex patterns
    - TLD and SLD extraction using the Public Suffix List
    - Command-line interface with optional domain parameter
    - Interactive mode when no domain is provided via command line

Dependencies:
    - publicsuffix2: For PSL data and domain parsing

Usage:
    python public_suffix.py [domain_name]

    Without arguments: Prompts for domain name interactively
    With domain argument: Analyzes the specified domain

Examples:
    python public_suffix.py example.com
    python public_suffix.py subdomain.example.co.uk
    python public_suffix.py  # Interactive mode

Author: sql-sith
Repository: sith-source-snippets
Version: 0.1
"""

import os
from publicsuffix2 import PublicSuffixList, fetch as psl_fetch
import re
import argparse
from typing import Optional

__all__ = ["new_public_suffix_list", "get_domain_name_tld_sld", "is_valid_domain"]


def new_public_suffix_list(psl_file_name: str | None = None) -> PublicSuffixList:
    if psl_file_name:
        return PublicSuffixList(open(psl_file_name, encoding="UTF-8"))
    else:
        return PublicSuffixList()


def find_nic_url_for_suffix(target_suffix):
    """Find NIC URL by locating suffix then searching backwards for nearest NIC URL"""

    psl_text = psl_fetch().read()
    lines = psl_text.splitlines()

    # Find the line number where our suffix appears
    target_line = -1
    for i, line in enumerate(lines):
        if line.strip() == target_suffix:
            target_line = i
            break

    if target_line == -1:
        return None

    # Search backwards from target line to find the NIC URL comment
    for i in range(target_line, -1, -1):
        line = lines[i].strip()
        if line.startswith("//") and "https://" in line:
            # Extract URL from this line
            url_match = re.search(r"https://[^\s]+", line)
            if url_match:
                return url_match.group()

    return None


def get_domain_name_tld_sld(domain_name: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract Top-Level Domain (TLD) and Second-Level Domain (SLD) from a
    domain name.

    Uses the Public Suffix List (PSL) to accurately identify the TLD and SLD
    components of a given domain name. The PSL helps distinguish between actual
    TLDs and subdomain components, especially for complex domains like .co.uk
    or .com.au.

    Args:
        domain_name (str): The fully qualified domain name to analyze.
            - Examples: 'example.com', 'subdomain.example.co.uk'

    Returns:
        tuple[Optional[str], Optional[str]]: A tuple containing:
            - tld (str or None): The top-level domain
                - (e.g., 'com', 'co.uk')
            - sld (str or None): The second-level domain
                - (e.g., 'example.com', 'example.co.uk')

    Examples:
        >>> get_domain_name_tld_sld('example.com')
        ('com', 'example.com')

        >>> get_domain_name_tld_sld('subdomain.example.co.uk')
        ('co.uk', 'example.co.uk')

        >>> get_domain_name_tld_sld('invalid')
        (None, None)

    Note:
        - Uses wildcard=False for TLD extraction to get exact matches
        - Uses strict=True for SLD extraction to enforce PSL rules
        - Returns None values if the domain cannot be parsed according to PSL
            rules
    """

    tld = psl.get_tld(domain=domain_name, strict=True, wildcard=False)
    nic = None
    if tld:
        nic = find_nic_url_for_suffix(target_suffix=tld)

    sld = psl.get_sld(domain=domain_name, strict=True, wildcard=False)
    return tld, sld, nic


def is_valid_domain(domain: str) -> bool:
    """
    Validate domain name format according to RFC standards.

    Performs comprehensive validation of domain name syntax using a regex
    pattern that checks for proper domain structure, length constraints, and
    character
    restrictions as defined by internet standards.

    The validation includes:
    - Total domain length between 1-253 characters
    - Domain segments (labels) between 1-63 characters each
    - Valid characters: letters (A-Z, a-z), digits (0-9), and hyphens (-)
    - No leading or trailing hyphens in any segment
    - TLD must contain only letters and be 2-63 characters long

    Args:
        domain (str): The domain name to validate.
            - Examples: 'example.com', 'sub-domain.example-site.org'

    Returns:
        bool:
            - True if the domain name is valid according to RFC standards,
            - False otherwise.

    Examples:
        >>> is_valid_domain('example.com')
        True

        >>> is_valid_domain('sub-domain.example.org')
        True

        >>> is_valid_domain('invalid-domain-')
        False

        >>> is_valid_domain(
            'justtoolongdomainnamethatshouldnotbevalidaccordingtorfcstandards.com')
        False

    Note:
        This validation is purely syntactic and does not check if the domain
        actually exists or is reachable. For existence validation, DNS lookup
        would be required.
    """

    domain_name_pattern = re.compile(
        r"^(?=.{1,253}$)(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}$"
    )

    return bool(domain_name_pattern.match(domain))


def get_user_input(prompt: str) -> str:
    return input(prompt).strip()


def parse_args():
    """
    Parse command-line arguments for domain name input with interactive
    fallback.

    Accepts an optional domain name as a positional command-line argument. If
    no domain is provided via command line, prompts the user interactively for
    input.

    Command-line usage:
        python script.py example.com          # Direct domain input
        python script.py                      # Interactive prompt

    Returns:
        argparse.Namespace: Parsed arguments with 'domain' attribute containing
            the domain name (either from command line or interactive input).

    Raises:
        SystemExit: If interactive input fails or user provides invalid input.
    """

    def existing_file(filepath):
        if not os.path.exists(filepath):
            raise argparse.ArgumentTypeError(f"File not found: {filepath}")
        return filepath

    parser = argparse.ArgumentParser(description="Domain name validator and PSL lookup")
    parser.add_argument(
        "--domain",
        "-d",
        dest="domain_name",
        type=str,
        nargs="?",
        help="Domain name to validate and analyze",
    )
    parser.add_argument(
        "--psl",
        "--file",
        dest="psl_file_name",
        type=existing_file,
        nargs="?",
        help="(optional) Name of local public suffix list file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        dest="verbose",
        help="(optional) Print helpful interpretation of results",
        action="store_true",
    )

    args = parser.parse_args()

    # parameter set validation:
    if args.psl_file_name is not None:
        if args.domain_name is None:
            parser.error(r"The --psl parameter requires --domain")
        else:
            args.psl_file_name = args.psl_file_name.strip()

    # parse domain:
    if not args.domain_name:
        try:
            args.domain_name = get_user_input(prompt="Enter a domain name: ")
            args.domain_name = args.domain_name.strip()
        except ValueError as e:
            print(e)
            exit(1)

    if not is_valid_domain(args.domain_name):
        parser.error(f"Invalid domain name: {args.domain_name}")

    return args


def print_domain_summary(args, domain_name, tld, sld, nic):
    if args.verbose is True:
        print("\nSummary:")
        print("--------")

        if (tld and sld and tld == sld) or (tld and not sld):
            print(f"{domain_name} appears to be a valid public suffix.")
            print(f"The NIC for {tld} is {nic}.")
        elif tld and sld and tld in sld:
            print(f"{domain_name} belongs to the public suffix {tld}.")
            print(f"{sld} is a the shortest potentially registerable portion of {sld}.")
            print(f"The NIC for {tld} is {nic}.")
        elif tld and sld and tld not in sld:
            print(f"WARNING: Inconsistent PSL data found for {domain_name}.")
            print(f"Public suffix {tld} and next-level label {sld} both found")
            print("but appear to be unrelated to each other.")
            print(f"The NIC for {tld} is {nic}.")
        elif not tld and sld:
            print(f"WARNING: Inconsistent PSL data found for {domain_name}.")
            print(
                f"No public suffix found, but {sld} was returned as a potentially registerable subdomain."
            )
        else:  # Both None
            print(f"Could not parse {domain_name} according to Public Suffix List rules.")

        print("")


if __name__ == "__main__":
    args = parse_args()

    if args.psl_file_name is not None:
        psl_file_name = args.psl_file_name
        psl = new_public_suffix_list(psl_file_name=psl_file_name)
    else:
        psl = new_public_suffix_list()

    if args.domain_name is not None:
        domain_name = args.domain_name

        tld, sld, nic = get_domain_name_tld_sld(domain_name)
        print(f"\nPSL has the following info for {domain_name}:")
        print(f"    tld: {tld}")
        print(f"    sld: {sld}")
        print(f"    nic: {nic}")

        if args.verbose:
            print_domain_summary(args, domain_name, tld, sld, nic)
