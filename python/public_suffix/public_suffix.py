
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
"""

# pip install publicsuffix2
from publicsuffix2 import PublicSuffixList
import re
import argparse
from typing import Optional

# Load PSL from the packaged snapshot (or from a file you maintain)
psl = PublicSuffixList()  # or PublicSuffixList(open('public_suffix_list.dat'))


def get_domain_name_tld_sld(
    domain_name: str
) -> tuple[Optional[str], Optional[str]]:
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

    tld = psl.get_tld(domain=domain_name, wildcard=False)
    sld = psl.get_sld(domain=domain_name, strict=True)
    return tld, sld


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
        r'^(?=.{1,253}$)(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}$'
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
    parser = argparse.ArgumentParser(
        description="Domain name validator and PSL lookup"
    )
    parser.add_argument(
        "domain",
        nargs="?",   # optional
        help="Domain name to validate and analyze"
    )
    args = parser.parse_args()

    if not args.domain:
        try:
            args.domain = get_user_input(prompt="Enter a domain name: ")
        except ValueError as e:
            print(e)
            exit(1)

    args.domain = args.domain.strip()
    return args


if __name__ == '__main__':
    args = parse_args()

    if args.domain:
        domain_name = args.domain.strip()

        if not is_valid_domain(domain_name):
            print(f"Invalid domain name: {domain_name}")
            exit(1)

        tld, sld = get_domain_name_tld_sld(domain_name)
        print(f"PSL has the following info for {domain_name}:")
        print(f"    tld: {tld}")
        print(f"    sld: {sld}")
