"""
Domain Name Validation and Public Suffix List (PSL) Analyzer

This script provides domain name validation and analysis using the Public
Suffix List (PSL). It can validate domain names according to RFC standards
and extract Top-Level Domain (TLD), Second-Level Domain (SLD), and Network
Information Center (NIC) information.

Features:
    - Domain name format validation using regex patterns
    - TLD and SLD extraction using the Public Suffix List
    - NIC URL lookup for domain registrars/authorities
    - Command-line interface with multiple options
    - Interactive mode for continuous domain analysis
    - Verbose mode for detailed result interpretation

Dependencies:
    - publicsuffix2: For PSL data and domain parsing

Usage:
    python public_suffix.py --domain DOMAIN [OPTIONS]
    python public_suffix.py [OPTIONS]                    # Interactive mode

Options:
    --domain, -d DOMAIN     Domain name to validate and analyze
    --psl, --file FILE      Use local Public Suffix List file
    --verbose, -v           Enable detailed result interpretation
    --help, -h              Show help message

Examples:
    python public_suffix.py --domain example.com
    python public_suffix.py -d example.co.uk --verbose
    python public_suffix.py -d example.com --psl local_psl.dat
    python public_suffix.py                             # Interactive mode

Interactive Mode:
    When no domain is specified, the script enters interactive mode where
    you can analyze multiple domains consecutively. Enter a blank domain
    name to exit.

Output Format:
    For each domain, displays:
    - Public suffix (TLD): The domain's public suffix per PSL
    - Registerable: The shortest registerable domain portion
    - NIC: URL of the Network Information Center for the TLD

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
_DOMAIN_NAME_USER_PROMPT = "\nEnter a domain name (enter a blank name to quit): "


def new_public_suffix_list(psl_file_name: str | None = None) -> PublicSuffixList:
    """
    Create a new PublicSuffixList instance from a local file or remote source.

    Creates a PublicSuffixList object for domain parsing and validation. If a
    local PSL file is provided, it reads from that file. Otherwise, it uses
    the default behavior which typically fetches the latest Public Suffix List
    from the internet.

    The Public Suffix List (PSL) is a cross-vendor initiative cataloging all
    known public suffixes - domain suffixes under which Internet users can
    directly register names. Examples include ".com", ".co.uk", ".github.io".

    Args:
        psl_file_name (str | None, optional):
            Path to a local Public Suffix List file in standard PSL format.
            If None, uses the default remote PSL source.
            Defaults to None.

    Returns:
        PublicSuffixList:
            Configured PublicSuffixList instance ready for domain analysis
            operations like suffix extraction and domain validation.

    Raises:
        FileNotFoundError: If psl_file_name is provided but the file doesn't exist.
        UnicodeDecodeError: If the PSL file contains invalid UTF-8 encoding.
        IOError: If there are network issues when fetching the remote PSL (when
            psl_file_name is None).

    Note:
        When using a local file, ensure it follows the standard PSL format
        (https://publicsuffix.org/list/). The remote PSL is typically more
        up-to-date but requires internet connectivity.
    """
    if psl_file_name:
        return PublicSuffixList(open(psl_file_name, encoding="UTF-8"))
    else:
        return PublicSuffixList()


def find_nic_url_for_suffix(target_suffix):
    """
    Find the Network Information Center (NIC) URL for a given public suffix.

    Searches the Public Suffix List (PSL) to locate the specified suffix and
    then searches backwards through the file to find the associated NIC URL
    comment. The PSL format includes NIC URLs in comment lines (starting with
    '//') that precede the suffix entries they govern.

    This function helps identify the registrar or authority responsible for
    managing domain registrations under a specific public suffix.

    Args:
        target_suffix (str):
            The public suffix to find the NIC URL for.
            Examples: 'com', 'co.uk', 'github.io', 'blogspot.com'

    Returns:
        str | None:
            The NIC URL if found, or None if:
            - The target suffix is not found in the PSL
            - No NIC URL comment exists above the suffix entry
            - The PSL cannot be fetched or parsed

    Examples:
        >>> find_nic_url_for_suffix('com')
        'https://www.verisign.com/domain-names/com-domain-names/'

        >>> find_nic_url_for_suffix('co.uk')
        'https://www.nominet.uk/'

        >>> find_nic_url_for_suffix('nonexistent.suffix')
        None

    Raises:
        IOError: If the PSL cannot be fetched from the remote source.
        UnicodeDecodeError: If the PSL content cannot be decoded as UTF-8.
    """

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
    Extract Top-Level Domain (TLD), Second-Level Domain (SLD), and NIC URL
    from a domain name.

    Uses the Public Suffix List (PSL) to accurately identify the TLD and SLD
    components of a given domain name, and finds the associated Network
    Information Center (NIC) URL for the TLD. The PSL helps distinguish
    between actual TLDs and subdomain components, especially for complex
    domains like .co.uk or .com.au.

    Args:
        domain_name (str): The fully qualified domain name to analyze.
            Examples: 'example.com', 'subdomain.example.co.uk'

    Returns:
        tuple[Optional[str], Optional[str], Optional[str]]: A tuple containing:
            - tld (str | None): The top-level domain/public suffix
                (e.g., 'com', 'co.uk', 'github.io')
            - sld (str | None): The second-level domain including the TLD
                (e.g., 'example.com', 'example.co.uk')
            - nic (str | None): The NIC URL for the TLD's registrar/authority
                (e.g., 'https://www.verisign.com/...' for .com domains)

    Examples:
        >>> get_domain_name_tld_sld('example.com')
        ('com', 'example.com', 'https://www.verisign.com/domain-names/com-domain-names/')

        >>> get_domain_name_tld_sld('subdomain.example.co.uk')
        ('co.uk', 'example.co.uk', 'https://www.nominet.uk/')

        >>> get_domain_name_tld_sld('invalid')
        (None, None, None)

    Note:
        - Uses wildcard=False and strict=True for PSL lookups to get exact matches
        - Returns None values if the domain cannot be parsed according to PSL rules
        - Requires a global 'psl' PublicSuffixList object to be available
        - NIC URL lookup may return None even if TLD is found (if no NIC URL exists in PSL)

    Raises:
        NameError: If the global 'psl' object is not defined.
        IOError: If NIC URL lookup fails due to PSL fetch issues.
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
    character restrictions as defined by internet standards (RFC 1035, RFC 1123).

    The validation enforces the following rules:
        - Total domain length: 1-253 characters
        - Domain labels (segments): 1-63 characters each
        - Valid characters: letters (A-Z, a-z), digits (0-9), and hyphens (-)
        - No leading or trailing hyphens in any label
        - TLD must contain only letters and be 2-63 characters long
        - Must contain at least one dot (.) separator

    Args:
        domain (str): The domain name to validate.
            Examples: 'example.com', 'sub-domain.example-site.org'

    Returns:
        bool: True if the domain name conforms to RFC standards, False otherwise.

    Examples:
        >>> is_valid_domain('example.com')
        True

        >>> is_valid_domain('sub-domain.example.org')
        True

        >>> is_valid_domain('test123.co.uk')
        True

        >>> is_valid_domain('invalid-domain-')
        False

        >>> is_valid_domain('toolong' + 'x' * 250 + '.com')
        False

        >>> is_valid_domain('no-tld-here')
        False

        >>> is_valid_domain('-invalid.com')
        False

    Note:
        This validation is purely syntactic and does not verify if the domain
        actually exists, is reachable, or has valid DNS records. For existence
        validation, DNS lookup or network connectivity checks would be required.
    """
    _DOMAIN_NAME_REGEX = r"^(?=.{1,253}$)(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}$"

    domain_name_pattern = re.compile(_DOMAIN_NAME_REGEX)
    return bool(domain_name_pattern.match(domain))


def get_user_input(prompt: str) -> str:
    """
    Get user input from the command line with whitespace trimming and error handling.

    Prompts the user for input using the provided prompt string and returns
    the user's response with leading and trailing whitespace removed. This is
    a robust wrapper around Python's built-in input() function that ensures
    consistent whitespace handling and graceful error recovery across the application.

    Args:
        prompt (str): The prompt message to display to the user.
            Should typically end with a colon or space for readability.

    Returns:
        str: The user's input with leading and trailing whitespace stripped.
            Returns an empty string if:
            - The user enters only whitespace
            - A ValueError occurs during input processing

    Examples:
        >>> get_user_input("Enter your name: ")
        # User types: "  John Doe  "
        'John Doe'

        >>> get_user_input("Domain name: ")
        # User types: "example.com"
        'example.com'

        >>> get_user_input("Press Enter to continue: ")
        # User presses Enter
        ''

    Raises:
        KeyboardInterrupt: If the user interrupts input with Ctrl+C.
        EOFError: If the user sends EOF (Ctrl+D on Unix, Ctrl+Z on Windows).

    Note:
        - This function blocks execution until the user provides input
        - ValueError exceptions are caught, printed, and result in empty string return
        - For non-blocking input or timeout functionality, consider using alternative
          approaches like threading or async input methods
    """

    try:
        return input(prompt).strip()
    except ValueError as e:
        print(e)
        return ""


def parse_args():
    """
    Parse command-line arguments for domain validation and PSL analysis.

    Configures and parses command-line arguments for the domain name validator.
    Supports domain input, custom PSL files, and verbose output options. If no
    domain is provided via command line, switches to interactive mode and prompts
    the user for input. Validates the domain format before returning results.

    Command-line usage:
        python script.py --domain example.com              # Basic domain analysis
        python script.py -d example.com --verbose          # With detailed output
        python script.py -d example.com --psl local.dat    # With custom PSL file
        python script.py                                   # Interactive mode

    Arguments:
        --domain, -d: Domain name to validate and analyze (optional)
        --psl, --file: Path to local Public Suffix List file (optional)
        --verbose, -v: Enable detailed result interpretation (optional flag)

    Returns:
        argparse.Namespace: Parsed arguments object with attributes:
            - domain_name (str): The domain to analyze (from CLI or interactive input)
            - psl_file_name (str | None): Path to custom PSL file, if provided
            - verbose (bool): Whether to enable verbose output mode

    Raises:
        SystemExit: If:
            - Invalid domain name format is provided
            - PSL file is specified but domain is missing
            - PSL file path doesn't exist
            - User provides invalid input in interactive mode
        argparse.ArgumentTypeError: If PSL file path is invalid

    Examples:
        >>> args = parse_args()  # Interactive mode
        # Prompts: "Enter a domain name..."
        >>> args.domain_name
        'user-entered-domain.com'

        >>> # Command line: python script.py -d example.com -v
        >>> args = parse_args()
        >>> args.domain_name, args.verbose
        ('example.com', True)

    Note:
        - Sets global 'interactive_mode' variable to track input method
        - Validates domain format using is_valid_domain() before returning
        - PSL file parameter requires domain parameter to be specified
        - Interactive mode continues until valid domain is entered or user quits
    """
    global interactive_mode
    interactive_mode = False

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
        interactive_mode = True
        args.domain_name = get_user_input(_DOMAIN_NAME_USER_PROMPT)

    if not is_valid_domain(args.domain_name):
        parser.error(f"Invalid domain name: {args.domain_name}")

    return args


def print_domain_summary(args, domain_name, tld, sld, nic):
    """
    Print a human-readable summary of domain analysis results.

    Displays an interpretive summary of the Public Suffix List (PSL) analysis
    results when verbose mode is enabled. The summary explains the relationship
    between the domain components and identifies potential data inconsistencies
    or parsing issues.

    The function analyzes the combination of TLD, SLD, and NIC data to provide
    contextual explanations about:
    - Whether the domain is itself a public suffix
    - The registerable portion of the domain
    - The responsible Network Information Center
    - Potential PSL data inconsistencies

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
            Must have a 'verbose' attribute (bool).
        domain_name (str): The original domain name being analyzed.
        tld (str | None): The top-level domain/public suffix found by PSL.
        sld (str | None): The second-level domain (registerable portion).
        nic (str | None): The NIC URL for the TLD's registrar/authority.

    Returns:
        None: This function only produces console output.

    Output Scenarios:
        - **Public suffix domain**: When domain is itself a public suffix
        - **Normal domain**: When domain belongs to a recognized public suffix
        - **Inconsistent data**: When PSL returns conflicting TLD/SLD information
        - **Parse failure**: When domain cannot be analyzed per PSL rules

    Examples:
        >>> # For a normal domain
        >>> print_domain_summary(args, 'example.com', 'com', 'example.com', 'https://...')
        # Outputs: "example.com belongs to the public suffix com."

        >>> # For a public suffix itself
        >>> print_domain_summary(args, 'co.uk', 'co.uk', 'co.uk', 'https://...')
        # Outputs: "co.uk appears to be a valid public suffix."

        >>> # When verbose=False
        >>> print_domain_summary(args, 'example.com', 'com', 'example.com', 'https://...')
        # Outputs: (nothing - function returns early)

    Note:
        - Only produces output when args.verbose is True
        - Includes WARNING messages for inconsistent PSL data
        - Always prints a blank line at the end for formatting
        - Handles all combinations of None/valid values for tld/sld/nic
    """
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
            print(f"No public suffix found, but {sld} was returned as potentially registerable.")
        else:  # Both None
            print(f"Could not parse {domain_name} according to Public Suffix List rules.")

        print("")


if __name__ == "__main__":
    interactive_mode = False
    args = parse_args()

    if args.psl_file_name is not None:
        psl = new_public_suffix_list(psl_file_name=args.psl_file_name)
    else:
        psl = new_public_suffix_list()

    domain_name = args.domain_name

    while True and domain_name:
        tld, sld, nic = get_domain_name_tld_sld(domain_name)
        print(f"\nPSL has the following info for {domain_name}:\n")
        print(f"    public suffix: {tld}")
        print(f"     registerable: {sld}")
        print(f"              nic: {nic}\n")

        if args.verbose:
            print_domain_summary(args, domain_name, tld, sld, nic)

        if interactive_mode:
            domain_name = get_user_input(_DOMAIN_NAME_USER_PROMPT)
        else:
            break
