#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
access_diff.py - human-readable diff of two SQL Server access-review JSON snapshots.

    python3 access_diff.py BEFORE.json AFTER.json [--csv FILE] [--report FILE] [--allow-mismatch]

The two inputs are the "before" and "after" collector outputs for ONE SQL Server
instance. The script matches every JSON object across the two files and writes:

    <after-name>.access-diff.csv   one row per change, column titles, opens in Excel
    <after-name>.access-diff.txt   narrative report for auditors

Both are written next to the AFTER file unless --csv / --report say otherwise.

What counts as a change
    - an object present in BEFORE and missing from AFTER      -> Removed
    - an object present in AFTER and missing from BEFORE      -> Added
    - a matched object whose access-relevant field changed    -> Changed
      (grant permission list / WITH GRANT OPTION / object count,
       user login mapping, AD account Enabled flag; see WATCHED_FIELDS)
    Any other field difference (timestamps, derived statistics) is ignored.

Objects are matched by their GUID first (GrantGuid, UserGuid, ...). Objects
without a GUID, or whose GUID changed between files, fall back to a natural key
built from names (database + principal + role + permission as applicable).

Exit codes
    0   ran fine (changes or not) and found no integrity warnings
    1   could not run: bad path, unreadable JSON, files from different instances
    2   ran, but found integrity warnings a human should look at
        (misfiled records, dangling references, same collection timestamp, ...)

Standard library only. Python 3.9 or newer. No pip, no venv.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import sys
from collections import OrderedDict, defaultdict

VERSION = "1.0.0"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_WARNINGS = 2

# --------------------------------------------------------------------------
# Section catalog. Edit here if the collector schema changes.
# --------------------------------------------------------------------------

# Order sections appear in the summary table and in the report.
SECTION_ORDER = [
    "Principals", "Users", "Roles", "RoleMemberships", "Grants",
    "AdAccounts", "AdGroupMemberships", "AdGroups",
    "Databases", "Procedures", "Listeners",
]

# Sections that represent access. Everything else is context.
ACCESS_SECTIONS = {
    "Principals", "Users", "Roles", "RoleMemberships", "Grants",
    "AdAccounts", "AdGroupMemberships", "AdGroups",
}

LABELS = {
    "Principals": "Server logins",
    "Users": "Database users",
    "Roles": "Database roles",
    "RoleMemberships": "Role memberships",
    "Grants": "Permission grants",
    "AdAccounts": "AD accounts",
    "AdGroupMemberships": "AD group memberships",
    "AdGroups": "AD groups",
    "Databases": "Databases",
    "Procedures": "Stored procedures",
    "Listeners": "AG listeners",
}

# The field that identifies one JSON object in each section. None = no GUID.
GUID_FIELD = {
    "Principals": "PrincipalGuid",
    "Users": "UserGuid",
    "Roles": "RoleGuid",
    "RoleMemberships": "RoleMembershipGuid",
    "Grants": "GrantGuid",
    "AdAccounts": "AdAccountGuid",
    "AdGroupMemberships": None,      # composite: AdAccountGuid + PrincipalGuid
    "AdGroups": "AdGroupGuid",       # shape unknown at time of writing
    "Databases": "DatabaseGuid",
    "Procedures": None,              # FullName
    "Listeners": "ListenerGuid",
}

# Field changes on a matched object that are themselves an access change.
WATCHED_FIELDS = {
    "Grants": ["Description", "WithGrantOption", "ObjCount"],
    "Users": ["LoginMapping"],
    "AdAccounts": ["Enabled"],
}

# How to recognize what kind of record an object is, regardless of which array
# it was found in. Checked in order; first match wins.
#   (section, fields that must be present, fields that must be absent)
SHAPES = [
    ("Grants",             {"GrantGuid"},                                set()),
    ("RoleMemberships",    {"RoleMembershipGuid"},                       set()),
    ("Roles",              {"RoleGuid", "DatabaseGuid"},                 set()),
    ("Users",              {"UserGuid", "DatabaseGuid"},                 set()),
    ("Databases",          {"DatabaseGuid", "DatabaseId"},               set()),
    ("Procedures",         {"FullName", "RW_SELF"},                      set()),
    ("Listeners",          {"ListenerGuid"},                             set()),
    ("AdGroupMemberships", {"AdAccountGuid", "PrincipalGuid", "IsDirect"}, set()),
    ("AdAccounts",         {"AdAccountGuid", "LoginName"},               set()),
    ("Principals",         {"PrincipalGuid", "Name", "TypeDesc"},
                           {"DatabaseGuid", "UserGuid", "AdAccountGuid"}),
]
# Sections whose record shape we do not know; records there are never "misfiled".
SHAPELESS = {"AdGroups"}

# Top-level scalar / object keys that must agree between the two files.
MUST_MATCH_SCALARS = ["SchemaVersion", "Division", "Environment"]
MUST_MATCH_INSTANCE = ["InstanceGuid", "ServerName"]

GROUP_SERVER = "Server level"
GROUP_AD = "Active Directory (group expansion)"
GROUP_CONTEXT = "Collection context (not access)"

CSV_COLUMNS = [
    "Section", "Change", "Summary",
    "Database", "Principal", "PrincipalType", "Role", "Permission", "Scope", "GrantType",
    "Field", "Before", "After",
    "ObjectGuidField", "ObjectGuid", "DatabaseGuid", "PrincipalGuid", "RoleGuid",
    "FoundIn",
]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

class Fatal(Exception):
    """Something that stops the run (exit code 1)."""


class Findings:
    """Collects WARNING (exit 2) and NOTE (informational) lines."""

    def __init__(self):
        self.warnings = []
        self.notes = []

    def warn(self, text):
        if text not in self.warnings:
            self.warnings.append(text)

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)


def show(v):
    """Render a JSON scalar the way it looks in the JSON file."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True, separators=(",", ":"))
    return str(v)


def s(v):
    """Scalar to string, None -> empty string."""
    return "" if v is None else str(v)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def classify(rec):
    if not isinstance(rec, dict):
        return None
    keys = set(rec)
    for section, must, must_not in SHAPES:
        if must <= keys and not (must_not & keys):
            return section
    return None


def kind_word(type_desc):
    """Turn a SQL Server TypeDesc into the word used in a sentence."""
    t = (type_desc or "").upper()
    if t == "WINDOWS_GROUP":
        return "Group"
    if t.endswith("_ROLE"):
        return "Role"
    if t.endswith("_LOGIN"):
        return "Login"
    if t.endswith("_USER"):
        return "User"
    return "Principal"


def scope_words(scope, obj_count):
    sc = (scope or "").upper()
    if sc == "OBJECT":
        n = obj_count if isinstance(obj_count, int) else None
        if n is None:
            return "object scope"
        return "object scope, %d object%s" % (n, "" if n == 1 else "s")
    if sc:
        return sc.lower() + " scope"
    return "unknown scope"


def split_perms(desc):
    return set(p.strip() for p in (desc or "").split(",") if p.strip())


def fmt_int(n):
    return "{:,}".format(n)


# --------------------------------------------------------------------------
# One loaded snapshot (one JSON file)
# --------------------------------------------------------------------------

class Rec:
    __slots__ = ("section", "raw", "ident", "ident_field", "nat", "group", "fields")

    def __init__(self, section, raw):
        self.section = section
        self.raw = raw
        self.ident = None
        self.ident_field = ""
        self.nat = ()
        self.group = GROUP_CONTEXT
        self.fields = {
            "Database": "", "Principal": "", "PrincipalType": "", "Role": "",
            "Permission": "", "Scope": "", "GrantType": "",
            "DatabaseGuid": "", "PrincipalGuid": "", "RoleGuid": "",
            "PrincipalGuidField": "", "DisplayName": "", "Extra": "",
        }


class Snapshot:
    def __init__(self, path, label, findings):
        self.path = path
        self.label = label
        self.findings = findings
        self.sections = OrderedDict((name, []) for name in SECTION_ORDER)
        self.extra_sections = OrderedDict()
        self.scalars = OrderedDict()
        self.recs = OrderedDict()
        self._dangling = defaultdict(list)     # (section, refField) -> [guid]

        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as e:
            raise Fatal("cannot read %s file %s: %s" % (label, path, e))
        self.size = len(raw)
        self.sha256 = hashlib.sha256(raw).hexdigest()
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError) as e:
            raise Fatal("%s file is not valid UTF-8 JSON (%s): %s" % (label, path, e))
        if not isinstance(data, dict):
            raise Fatal("%s file %s: top level is %s, expected a JSON object"
                        % (label, path, type(data).__name__))
        self.data = data

        self._load_sections()
        self._build_lookups()
        for name in list(self.sections) + list(self.extra_sections):
            source = self.sections.get(name)
            if source is None:
                source = self.extra_sections[name]
            self.recs[name] = [self._build_rec(name, r) for r in source]
        self._report_dangling()

    # -- loading -----------------------------------------------------------

    def _load_sections(self):
        misfiled = defaultdict(int)
        unknown_shape = defaultdict(int)
        for key, val in self.data.items():
            if isinstance(val, list):
                if key in self.sections:
                    for rec in val:
                        target = classify(rec)
                        if target is None:
                            target = key
                            if key not in SHAPELESS:
                                unknown_shape[key] += 1
                        elif target != key:
                            misfiled[(key, target)] += 1
                        self.sections[target].append(rec)
                else:
                    self.extra_sections[key] = val
                    self.findings.warn(
                        "[%s] unknown top-level section '%s' (%d records); compared "
                        "generically, whole record as identity" % (self.label, key, len(val)))
            else:
                self.scalars[key] = val
        for name in self.sections:
            if name not in self.data:
                self.findings.warn(
                    "[%s] section '%s' is missing from the file; treated as empty"
                    % (self.label, name))
        for (found_in, really), n in sorted(misfiled.items()):
            self.findings.warn(
                "[%s] %d record(s) inside '%s' have the shape of '%s' records. They were "
                "compared as %s. The collector should never do this; this file may have "
                "been edited by hand." % (self.label, n, found_in, really, really))
        for name, n in sorted(unknown_shape.items()):
            self.findings.warn(
                "[%s] %d record(s) in '%s' have an unrecognized field layout; compared as-is"
                % (self.label, n, name))

    def _build_lookups(self):
        def by(section, field):
            out = {}
            for r in self.sections.get(section, []):
                if isinstance(r, dict) and r.get(field) is not None:
                    out.setdefault(str(r[field]), r)
            return out
        self.dbs = by("Databases", "DatabaseGuid")
        self.users = by("Users", "UserGuid")
        self.roles = by("Roles", "RoleGuid")
        self.principals = by("Principals", "PrincipalGuid")
        self.adaccounts = by("AdAccounts", "AdAccountGuid")

    def _resolve(self, table, guid, section, ref_field, name_field="Name"):
        """Return (name, record) for a GUID reference; note dangling references."""
        if guid is None:
            return ("<no %s>" % ref_field, None)
        rec = table.get(str(guid))
        if rec is None:
            self._dangling[(section, ref_field)].append(str(guid))
            return ("<unresolved %s %s>" % (ref_field, guid), None)
        return (s(rec.get(name_field)) or "<unnamed>", rec)

    def _report_dangling(self):
        for (section, ref_field), guids in sorted(self._dangling.items()):
            uniq = sorted(set(guids))
            self.findings.warn(
                "[%s] %d %s record(s) reference a %s that does not exist in this file "
                "(e.g. %s). Sentences for those records show '<unresolved ...>'."
                % (self.label, len(guids), section, ref_field, uniq[0]))

    # -- per-record interpretation ------------------------------------------

    def _build_rec(self, section, raw):
        r = Rec(section, raw)
        f = r.fields
        if not isinstance(raw, dict):
            r.ident = canonical(raw)
            r.ident_field = "(whole record)"
            r.nat = (r.ident,)
            return r

        gf = GUID_FIELD.get(section)
        if gf and raw.get(gf) is not None:
            r.ident = str(raw[gf])
            r.ident_field = gf

        if section == "Principals":
            f["Principal"] = s(raw.get("Name"))
            f["PrincipalType"] = s(raw.get("TypeDesc"))
            f["PrincipalGuid"] = s(raw.get("PrincipalGuid"))
            f["PrincipalGuidField"] = "PrincipalGuid"
            f["Extra"] = s(raw.get("Designation"))
            r.nat = (f["Principal"],)
            r.group = GROUP_SERVER

        elif section == "Users":
            db, _ = self._resolve(self.dbs, raw.get("DatabaseGuid"), section, "DatabaseGuid")
            f["Database"], f["DatabaseGuid"] = db, s(raw.get("DatabaseGuid"))
            f["Principal"] = s(raw.get("Name"))
            f["PrincipalType"] = s(raw.get("TypeDesc"))
            f["PrincipalGuid"] = s(raw.get("UserGuid"))
            f["PrincipalGuidField"] = "UserGuid"
            f["Extra"] = s(raw.get("LoginMapping"))
            r.nat = (db, f["Principal"])
            r.group = "Database: " + db

        elif section == "Roles":
            db, _ = self._resolve(self.dbs, raw.get("DatabaseGuid"), section, "DatabaseGuid")
            f["Database"], f["DatabaseGuid"] = db, s(raw.get("DatabaseGuid"))
            f["Role"] = s(raw.get("Name"))
            f["RoleGuid"] = s(raw.get("RoleGuid"))
            f["PrincipalType"] = s(raw.get("TypeDesc")) or "DATABASE_ROLE"
            f["Extra"] = s(raw.get("Category"))
            r.nat = (db, f["Role"])
            r.group = "Database: " + db

        elif section == "RoleMemberships":
            db, _ = self._resolve(self.dbs, raw.get("DatabaseGuid"), section, "DatabaseGuid")
            role, _ = self._resolve(self.roles, raw.get("RoleGuid"), section, "RoleGuid")
            f["Database"], f["DatabaseGuid"] = db, s(raw.get("DatabaseGuid"))
            f["Role"], f["RoleGuid"] = role, s(raw.get("RoleGuid"))
            f["PrincipalGuid"] = s(raw.get("MemberGuid"))
            f["PrincipalGuidField"] = "MemberGuid"
            if s(raw.get("MemberType")).upper() == "ROLE":
                member, mrec = self._resolve(self.roles, raw.get("MemberGuid"), section, "MemberGuid (role)")
                f["PrincipalType"] = "DATABASE_ROLE"
            else:
                member, mrec = self._resolve(self.users, raw.get("MemberGuid"), section, "MemberGuid (user)")
                f["PrincipalType"] = s(mrec.get("TypeDesc")) if mrec else "UNKNOWN"
            f["Principal"] = member
            r.nat = (db, role, member)
            r.group = "Database: " + db

        elif section == "Grants":
            db, _ = self._resolve(self.dbs, raw.get("DatabaseGuid"), section, "DatabaseGuid")
            f["Database"], f["DatabaseGuid"] = db, s(raw.get("DatabaseGuid"))
            if raw.get("UserGuid") is not None:
                grantee, grec = self._resolve(self.users, raw.get("UserGuid"), section, "UserGuid")
                f["PrincipalType"] = s(grec.get("TypeDesc")) if grec else "UNKNOWN"
                f["PrincipalGuid"] = s(raw.get("UserGuid"))
                f["PrincipalGuidField"] = "UserGuid"
            elif raw.get("RoleGuid") is not None:
                grantee, grec = self._resolve(self.roles, raw.get("RoleGuid"), section, "RoleGuid")
                f["PrincipalType"] = "DATABASE_ROLE"
                f["PrincipalGuid"] = s(raw.get("RoleGuid"))
                f["PrincipalGuidField"] = "RoleGuid"
                f["Role"], f["RoleGuid"] = grantee, s(raw.get("RoleGuid"))
            else:
                grantee = "<no grantee>"
                self._dangling[(section, "UserGuid/RoleGuid both null")].append(r.ident or "?")
            f["Principal"] = grantee
            f["Permission"] = s(raw.get("Description"))
            f["Scope"] = s(raw.get("Scope"))
            f["GrantType"] = s(raw.get("GrantType"))
            r.nat = (db, grantee, f["GrantType"], f["Scope"], f["Permission"])
            r.group = "Database: " + db

        elif section == "AdAccounts":
            f["Principal"] = s(raw.get("LoginName")) or s(raw.get("SamAccountName")) or s(raw.get("Sid"))
            f["PrincipalType"] = "AD_" + (s(raw.get("ObjectClass")).upper() or "ACCOUNT")
            f["PrincipalGuid"] = s(raw.get("AdAccountGuid"))
            f["PrincipalGuidField"] = "AdAccountGuid"
            f["DisplayName"] = s(raw.get("DisplayName"))
            f["Extra"] = s(raw.get("Designation"))
            r.nat = (f["Principal"],)
            r.group = GROUP_AD

        elif section == "AdGroupMemberships":
            acct, arec = self._resolve(self.adaccounts, raw.get("AdAccountGuid"), section,
                                       "AdAccountGuid", name_field="LoginName")
            grp, _ = self._resolve(self.principals, raw.get("PrincipalGuid"), section, "PrincipalGuid")
            f["Principal"] = acct
            f["PrincipalType"] = "AD_" + (s(arec.get("ObjectClass")).upper() if arec else "ACCOUNT")
            f["PrincipalGuid"] = s(raw.get("AdAccountGuid"))
            f["PrincipalGuidField"] = "AdAccountGuid"
            f["DisplayName"] = s(arec.get("DisplayName")) if arec else ""
            f["Role"] = grp
            f["RoleGuid"] = s(raw.get("PrincipalGuid"))
            f["Extra"] = "direct" if raw.get("IsDirect") else "indirect"
            r.ident = "%s|%s" % (s(raw.get("AdAccountGuid")), s(raw.get("PrincipalGuid")))
            r.ident_field = "AdAccountGuid+PrincipalGuid"
            r.nat = (acct, grp)
            r.group = GROUP_AD

        elif section == "Databases":
            f["Database"] = s(raw.get("Name"))
            f["DatabaseGuid"] = s(raw.get("DatabaseGuid"))
            f["Extra"] = s(raw.get("State"))
            r.nat = (f["Database"],)
            r.group = GROUP_CONTEXT

        elif section == "Procedures":
            f["Database"] = s(raw.get("Database"))
            f["Extra"] = s(raw.get("FullName"))
            r.ident = s(raw.get("FullName")) or canonical(raw)
            r.ident_field = "FullName"
            r.nat = (r.ident,)
            r.group = GROUP_CONTEXT

        elif section == "Listeners":
            f["Extra"] = "%s:%s" % (s(raw.get("ListenerName")), s(raw.get("Port")))
            r.nat = (s(raw.get("ListenerName")), s(raw.get("Port")))
            r.group = GROUP_CONTEXT

        else:
            # AdGroups (shape unknown) and any unknown section: whole record is the identity.
            if r.ident is None:
                r.ident = canonical(raw)
                r.ident_field = "(whole record)"
            f["Principal"] = s(raw.get("Name")) or s(raw.get("LoginName"))
            r.nat = (r.ident,)
            r.group = GROUP_AD if section.startswith("Ad") else GROUP_CONTEXT

        return r


# --------------------------------------------------------------------------
# Sentences
# --------------------------------------------------------------------------

def _who(f):
    return "%s %s" % (kind_word(f["PrincipalType"]), f["Principal"])


def _ad_who(f):
    name = f["Principal"]
    if f["DisplayName"]:
        name += " (%s)" % f["DisplayName"]
    return name


def sentence(rec, change):
    """One plain-English line for a Removed / Added object."""
    f = rec.fields
    sec = rec.section
    removed = (change == "Removed")

    if sec == "Principals":
        return "%s was %s the server" % (_who(f), "removed from" if removed else "added to")

    if sec == "Users":
        return "%s was %s database %s" % (_who(f), "removed from" if removed else "added to", f["Database"])

    if sec == "Roles":
        cat = " (%s)" % f["Extra"] if f["Extra"] else ""
        return "Role %s%s was %s database %s" % (
            f["Role"], cat, "removed from" if removed else "added to", f["Database"])

    if sec == "RoleMemberships":
        return "%s was %s role %s in database %s" % (
            _who(f), "removed from" if removed else "added to", f["Role"], f["Database"])

    if sec == "Grants":
        raw = rec.raw
        sw = scope_words(f["Scope"], raw.get("ObjCount"))
        wgo = ", WITH GRANT OPTION" if raw.get("WithGrantOption") else ""
        if f["GrantType"].upper() == "DENY":
            text = "DENY of %s (%s) on %s was %s in database %s" % (
                f["Permission"], sw, _who(f), "removed" if removed else "added", f["Database"])
            if removed:
                text += " - note: removing a DENY increases access"
            return text
        return "%s: %s (%s%s) was %s in database %s" % (
            _who(f), f["Permission"], sw, wgo, "revoked" if removed else "granted", f["Database"])

    if sec == "AdAccounts":
        return "AD account %s %s the collected AD accounts" % (
            _ad_who(f), "is no longer present in" if removed else "newly appears in")

    if sec == "AdGroupMemberships":
        ind = " (indirect membership)" if f["Extra"] == "indirect" else ""
        return "AD account %s was %s AD group %s%s" % (
            _ad_who(f), "removed from" if removed else "added to", f["Role"], ind)

    if sec == "Databases":
        return "Database %s %s the collection" % (
            f["Database"], "is no longer present in" if removed else "newly appears in")

    if sec == "Procedures":
        return "Stored procedure %s %s the collection" % (
            f["Extra"], "is no longer present in" if removed else "newly appears in")

    if sec == "Listeners":
        return "Listener %s %s the collection" % (
            f["Extra"], "is no longer present in" if removed else "newly appears in")

    return "%s record was %s: %s" % (sec, "removed" if removed else "added", canonical(rec.raw))


def change_sentence(rec, field, before, after):
    """One plain-English line for a watched-field change on a matched object."""
    f = rec.fields
    sec = rec.section
    if sec == "Grants":
        sw = scope_words(f["Scope"], rec.raw.get("ObjCount"))
        if field == "Description":
            b, a = split_perms(before), split_perms(after)
            text = "%s: permissions in database %s (%s) changed from '%s' to '%s'" % (
                _who(f), f["Database"], sw, show(before), show(after))
            if b - a:
                text += "; revoked: " + ", ".join(sorted(b - a))
            if a - b:
                text += "; granted: " + ", ".join(sorted(a - b))
            return text
        if field == "WithGrantOption":
            return "%s: WITH GRANT OPTION on %s (%s) in database %s changed from %s to %s" % (
                _who(f), f["Permission"], sw, f["Database"], show(before), show(after))
        if field == "ObjCount":
            return "%s: %s (%s) in database %s now covers %s object(s), was %s" % (
                _who(f), f["Permission"], f["Scope"].lower() + " scope", f["Database"],
                show(after), show(before))
    if sec == "Users" and field == "LoginMapping":
        return "%s in database %s: login mapping changed from %s to %s" % (
            _who(f), f["Database"], show(before), show(after))
    if sec == "AdAccounts" and field == "Enabled":
        tail = " (account disabled)" if after is False else ""
        return "AD account %s: Enabled changed from %s to %s%s" % (
            _ad_who(f), show(before), show(after), tail)
    return "%s %s: %s changed from %s to %s" % (sec, rec.ident, field, show(before), show(after))


# --------------------------------------------------------------------------
# Diffing
# --------------------------------------------------------------------------

def make_row(rec, change, text, field="", before="", after=""):
    f = rec.fields
    found_in = {"Removed": "before", "Added": "after"}.get(change, "both")
    return {
        "Section": rec.section,
        "Change": change,
        "Summary": text,
        "Database": f["Database"],
        "Principal": f["Principal"],
        "PrincipalType": f["PrincipalType"],
        "Role": f["Role"],
        "Permission": f["Permission"],
        "Scope": f["Scope"],
        "GrantType": f["GrantType"],
        "Field": field,
        "Before": before,
        "After": after,
        "ObjectGuidField": rec.ident_field,
        "ObjectGuid": rec.ident or "",
        "DatabaseGuid": f["DatabaseGuid"],
        "PrincipalGuid": f["PrincipalGuid"],
        "RoleGuid": f["RoleGuid"],
        "FoundIn": found_in,
        "_group": rec.group,
        "_rec": rec,
    }


def index_by_identity(recs, snap, section, findings):
    idx = OrderedDict()
    dup_count = defaultdict(int)
    for r in recs:
        key = r.ident if r.ident is not None else "NAT:" + "|".join(r.nat)
        if key in idx:
            dup_count[key] += 1
            key = "%s#dup%d" % (key, dup_count[key])
        idx[key] = r
    if dup_count:
        first = next(iter(dup_count))
        findings.warn(
            "[%s] %s: %d identity value(s) occur more than once (e.g. %s). Duplicates "
            "were kept and compared separately." % (snap.label, section, len(dup_count), first))
    return idx


def pair_by_natural_key(b_left, a_left):
    """Match leftovers by natural key. Returns (pairs, still_b, still_a)."""
    bn, an = defaultdict(list), defaultdict(list)
    for r in b_left:
        bn[r.nat].append(r)
    for r in a_left:
        an[r.nat].append(r)
    pairs, still_b, still_a = [], [], []
    for key in list(bn.keys()) + [k for k in an if k not in bn]:
        bl, al = bn.get(key, []), an.get(key, [])
        n = min(len(bl), len(al))
        pairs.extend(zip(bl[:n], al[:n]))
        still_b.extend(bl[n:])
        still_a.extend(al[n:])
    return pairs, still_b, still_a


def pair_grants_by_slot(b_left, a_left):
    """Grants only: a partial revoke on a re-minted GrantGuid looks like one
    removal plus one addition. If exactly one leftover on each side shares
    (database, grantee, GrantType, Scope), treat it as the same grant changed."""
    def slot(r):
        f = r.fields
        # Names, not GUIDs, so this still works if the collector re-mints UserGuid/RoleGuid.
        return (f["Database"], f["PrincipalGuidField"], f["Principal"], f["GrantType"], f["Scope"])
    bs, as_ = defaultdict(list), defaultdict(list)
    for r in b_left:
        bs[slot(r)].append(r)
    for r in a_left:
        as_[slot(r)].append(r)
    pairs, used_b, used_a = [], set(), set()
    for key, bl in bs.items():
        al = as_.get(key, [])
        if len(bl) == 1 and len(al) == 1:
            pairs.append((bl[0], al[0]))
            used_b.add(id(bl[0]))
            used_a.add(id(al[0]))
    still_b = [r for r in b_left if id(r) not in used_b]
    still_a = [r for r in a_left if id(r) not in used_a]
    return pairs, still_b, still_a


def diff_section(section, before, after, findings):
    b_recs = before.recs.get(section, [])
    a_recs = after.recs.get(section, [])
    bi = index_by_identity(b_recs, before, section, findings)
    ai = index_by_identity(a_recs, after, section, findings)

    matched = [(bi[k], ai[k]) for k in bi if k in ai]
    b_left = [r for k, r in bi.items() if k not in ai]
    a_left = [r for k, r in ai.items() if k not in bi]

    rekeyed, b_left, a_left = pair_by_natural_key(b_left, a_left)
    if rekeyed:
        examples = "; ".join(" / ".join(x for x in p[0].nat if x) for p in rekeyed[:3])
        ident = GUID_FIELD.get(section) or "identity"
        total_matched = len(matched) + len(rekeyed)
        if len(rekeyed) >= max(10, total_matched // 2):
            findings.warn(
                "%s: %d of %d matched record(s) carry a different %s in the two files. The "
                "collector appears to generate %s fresh on every run, so records were matched "
                "by name instead. This is fine for the diff, but the GUIDs in the two JSON "
                "files will not line up for this section." % (
                    section, len(rekeyed), total_matched, ident, ident))
        else:
            findings.warn(
                "%s: %d record(s) match by name but carry a different %s in the two files "
                "(dropped and re-created?). Treated as the same object. E.g. %s"
                % (section, len(rekeyed), ident, examples))
    matched.extend(rekeyed)

    rows = []
    if section == "Grants":
        slot_pairs, b_left, a_left = pair_grants_by_slot(b_left, a_left)
        for b, a in slot_pairs:
            findings.note(
                "Grants: %s / %s / %s %s: GrantGuid differs between files (%s -> %s) but it "
                "is the only grant in that slot on both sides; reported as a permission "
                "change, not as a removal plus an addition."
                % (b.fields["Database"], b.fields["Principal"], b.fields["GrantType"],
                   b.fields["Scope"], b.ident, a.ident))
        matched.extend(slot_pairs)

    for r in b_left:
        rows.append(make_row(r, "Removed", sentence(r, "Removed")))
    for r in a_left:
        rows.append(make_row(r, "Added", sentence(r, "Added")))

    changed = 0
    for b, a in matched:
        if not (isinstance(b.raw, dict) and isinstance(a.raw, dict)):
            continue
        any_change = False
        for field in WATCHED_FIELDS.get(section, []):
            bv, av = b.raw.get(field), a.raw.get(field)
            if bv != av:
                any_change = True
                rows.append(make_row(a, "Changed", change_sentence(b, field, bv, av),
                                     field=field, before=show(bv), after=show(av)))
        if any_change:
            changed += 1

    return {
        "section": section,
        "before": len(b_recs),
        "after": len(a_recs),
        "removed": len(b_left),
        "added": len(a_left),
        "changed": changed,
        "rows": rows,
    }


# --------------------------------------------------------------------------
# File-level compatibility checks
# --------------------------------------------------------------------------

def check_compatibility(before, after, allow_mismatch, findings):
    problems = []
    for key in MUST_MATCH_SCALARS:
        bv, av = before.scalars.get(key), after.scalars.get(key)
        if bv != av:
            problems.append("%s differs: before=%s after=%s" % (key, show(bv), show(av)))
    bi = before.scalars.get("Instance") or {}
    ai = after.scalars.get("Instance") or {}
    if not isinstance(bi, dict) or not isinstance(ai, dict):
        problems.append("Instance block missing or malformed in one of the files")
        bi, ai = {}, {}
    for key in MUST_MATCH_INSTANCE:
        if bi.get(key) != ai.get(key):
            problems.append("Instance.%s differs: before=%s after=%s"
                            % (key, show(bi.get(key)), show(ai.get(key))))
    if problems:
        if not allow_mismatch:
            raise Fatal(
                "the two files do not describe the same instance / collector version:\n  - "
                + "\n  - ".join(problems)
                + "\nRe-run with --allow-mismatch if this is intentional.")
        for p in problems:
            findings.warn("MISMATCH ACCEPTED (--allow-mismatch): " + p)

    for key in sorted(set(bi) | set(ai)):
        if key in MUST_MATCH_INSTANCE:
            continue
        if bi.get(key) != ai.get(key):
            findings.note("Instance.%s changed between collections: %s -> %s"
                          % (key, show(bi.get(key)), show(ai.get(key))))

    bc = before.scalars.get("Collection") or {}
    ac = after.scalars.get("Collection") or {}
    if isinstance(bc, dict) and isinstance(ac, dict):
        bt, at = s(bc.get("CollectedAtUtc")), s(ac.get("CollectedAtUtc"))
        if bt and bt == at:
            findings.warn(
                "Both files carry the same Collection.CollectedAtUtc (%s). The AFTER file "
                "may be an edited copy of BEFORE rather than a fresh collection." % bt)
        elif bt and at and at < bt:
            findings.warn(
                "AFTER was collected earlier (%s) than BEFORE (%s). Check the file order."
                % (at, bt))
        if bc.get("CollectedByLogin") != ac.get("CollectedByLogin"):
            findings.note("Collected by different logins: before=%s after=%s"
                          % (show(bc.get("CollectedByLogin")), show(ac.get("CollectedByLogin"))))
        if bc.get("Permissions") != ac.get("Permissions"):
            findings.warn(
                "The collector ran with different permissions in the two files "
                "(Collection.Permissions before=%s after=%s). Missing data could look like "
                "removed access." % (show(bc.get("Permissions")), show(ac.get("Permissions"))))
        if bc.get("DatabaseScope") != ac.get("DatabaseScope"):
            findings.warn("Collection.DatabaseScope differs: before=%s after=%s"
                          % (show(bc.get("DatabaseScope")), show(ac.get("DatabaseScope"))))
        for label, c in (("before", bc), ("after", ac)):
            w = c.get("Warnings")
            if isinstance(w, list) and w:
                findings.note("[%s] the collector itself reported %d warning(s): %s"
                              % (label, len(w), "; ".join(show(x) for x in w[:5])))


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore",
                           lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def text_table(headers, rows, right_align=()):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    def fmt(row):
        cells = []
        for i, cell in enumerate(row):
            cells.append(cell.rjust(widths[i]) if i in right_align else cell.ljust(widths[i]))
        return "  ".join(cells).rstrip()
    lines = [fmt(headers), "  ".join("-" * w for w in widths)]
    lines.extend(fmt(r) for r in rows)
    return lines


def group_sort_key(group):
    if group == GROUP_SERVER:
        return (0, "")
    if group == GROUP_AD:
        return (1, "")
    if group == GROUP_CONTEXT:
        return (3, "")
    return (2, group.lower())


def row_sort_key(row):
    sec = row["Section"]
    sec_i = SECTION_ORDER.index(sec) if sec in SECTION_ORDER else len(SECTION_ORDER)
    return (row["Principal"].lower(), sec_i, row["Role"].lower(), row["Permission"].lower(),
            row["Field"])


def render_detail_block(title, rows, blurb=None):
    lines = [title, "-" * len(title)]
    if blurb:
        lines.append(blurb)
    if not rows:
        lines.append("  (none)")
        lines.append("")
        return lines
    by_group = defaultdict(list)
    for row in rows:
        by_group[row["_group"]].append(row)
    for group in sorted(by_group, key=group_sort_key):
        lines.append("")
        lines.append(group)
        for row in sorted(by_group[group], key=row_sort_key):
            lines.append("  [%s] %s" % (row["Section"], row["Summary"]))
            ids = []
            if row["ObjectGuid"]:
                ids.append("%s: %s" % (row["ObjectGuidField"], row["ObjectGuid"]))
            f = row["_rec"].fields
            if f["PrincipalGuid"] and f["PrincipalGuidField"] != row["ObjectGuidField"]:
                ids.append("%s: %s" % (f["PrincipalGuidField"], f["PrincipalGuid"]))
            if row["Section"] == "RoleMemberships" and f["RoleGuid"]:
                ids.append("RoleGuid: %s" % f["RoleGuid"])
            if row["Section"] == "AdGroupMemberships" and f["RoleGuid"]:
                ids.append("group PrincipalGuid: %s" % f["RoleGuid"])
            if row["DatabaseGuid"]:
                ids.append("DatabaseGuid: %s" % row["DatabaseGuid"])
            if ids:
                lines.append("      " + "   ".join(ids))
    lines.append("")
    return lines


def render_report(before, after, results, findings, args_text, generated):
    all_rows = [r for res in results for r in res["rows"]]
    removed = [r for r in all_rows if r["Change"] == "Removed"]
    added = [r for r in all_rows if r["Change"] == "Added"]
    changed = [r for r in all_rows if r["Change"] == "Changed"]
    access_rows = lambda rows: [r for r in rows if r["Section"] in ACCESS_SECTIONS]
    context_rows = lambda rows: [r for r in rows if r["Section"] not in ACCESS_SECTIONS]

    inst = after.scalars.get("Instance") or {}
    bc = before.scalars.get("Collection") or {}
    ac = after.scalars.get("Collection") or {}

    L = []
    title = "ACCESS REVIEW - BEFORE / AFTER DIFF"
    L += [title, "=" * len(title), ""]
    L.append("Generated:       %s by access_diff.py %s" % (generated, VERSION))
    L.append("Command:         %s" % args_text)
    L.append("Instance:        %s   (Division %s, Environment %s)" % (
        show(inst.get("ServerName")), show(after.scalars.get("Division")),
        show(after.scalars.get("Environment"))))
    L.append("InstanceGuid:    %s" % show(inst.get("InstanceGuid")))
    L.append("SQL Server:      %s %s %s" % (
        show(inst.get("VersionName")), show(inst.get("ProductLevel")), show(inst.get("ProductUpdateLevel"))))
    L.append("Schema version:  before %s / after %s" % (
        show(before.scalars.get("SchemaVersion")), show(after.scalars.get("SchemaVersion"))))
    L.append("")
    for label, snap, coll in (("BEFORE", before, bc), ("AFTER", after, ac)):
        L.append("%-7s %s" % (label, snap.path))
        L.append("        collected %s UTC by %s" % (
            show(coll.get("CollectedAtUtc")), show(coll.get("CollectedByLogin"))))
        L.append("        %s bytes, SHA-256 %s" % (fmt_int(snap.size), snap.sha256))
    L.append("")

    # Summary table
    L += ["SUMMARY", "-------"]
    trows = []
    for res in results:
        sec = res["section"]
        label = LABELS.get(sec, sec)
        trows.append([
            "%s (%s)" % (label, sec) if label != sec else sec,
            fmt_int(res["before"]), fmt_int(res["after"]),
            fmt_int(res["removed"]), fmt_int(res["added"]), fmt_int(res["changed"]),
            "access" if sec in ACCESS_SECTIONS else "context",
        ])
    L += text_table(["Section", "Before", "After", "Removed", "Added", "Changed", "Kind"],
                    trows, right_align={1, 2, 3, 4, 5})
    L.append("")
    ar, aa, ac_ = access_rows(removed), access_rows(added), access_rows(changed)
    L.append("Access changes:  %d removal(s), %d addition(s), %d change(s) on matched objects"
             % (len(ar), len(aa), len(ac_)))
    L.append("Context changes: %d removal(s), %d addition(s)"
             % (len(context_rows(removed)), len(context_rows(added))))
    L.append("")

    # Warnings / notes
    hdr = "WARNINGS (%d) - these set exit code 2 and need a human look" % len(findings.warnings)
    L += [hdr, "-" * len(hdr)]
    if findings.warnings:
        for i, w in enumerate(findings.warnings, 1):
            L.append("  W%d. %s" % (i, w))
    else:
        L.append("  (none)")
    L.append("")
    if findings.notes:
        hdr = "NOTES (%d) - informational" % len(findings.notes)
        L += [hdr, "-" * len(hdr)]
        for i, n in enumerate(findings.notes, 1):
            L.append("  N%d. %s" % (i, n))
        L.append("")

    # Details
    L += render_detail_block("ACCESS REMOVED", ar,
                             "Objects present in BEFORE and absent from AFTER.")
    L += render_detail_block("ACCESS CHANGED ON MATCHED OBJECTS", ac_,
                             "Same object in both files; an access-relevant field differs.")
    L += render_detail_block(
        "ACCESS ADDED - out of scope for a removal review, verify each one", aa,
        "Objects present in AFTER and absent from BEFORE.")
    ctx = context_rows(removed) + context_rows(added)
    L += render_detail_block("CONTEXT CHANGES (databases, procedures, listeners)", ctx)

    # Unchanged confirmation
    L += ["SECTIONS WITH NO CHANGES", "------------------------"]
    none_changed = True
    for res in results:
        if res["removed"] == 0 and res["added"] == 0 and res["changed"] == 0:
            none_changed = False
            L.append("  %-22s %s -> %s records, no changes" % (
                res["section"], fmt_int(res["before"]), fmt_int(res["after"])))
    if none_changed:
        L.append("  (every section has at least one change)")
    L.append("")

    L += ["HOW TO READ THIS", "----------------",
          "  Each line names the JSON array (in brackets) the object came from, then describes",
          "  the change in plain words. The line beneath gives the GUID(s) to search for in the",
          "  JSON files: the object's own GUID first, then the principal and database GUIDs.",
          "  Removed objects are in the BEFORE file; added objects are in the AFTER file.",
          "  The CSV written alongside this report has the same rows with one column per field.",
          ""]
    return "\n".join(L) + "\n"


def result_lines(results, findings, exit_code, csv_path, report_path):
    all_rows = [r for res in results for r in res["rows"] if r["Section"] in ACCESS_SECTIONS]
    n_rem = sum(1 for r in all_rows if r["Change"] == "Removed")
    n_add = sum(1 for r in all_rows if r["Change"] == "Added")
    n_chg = sum(1 for r in all_rows if r["Change"] == "Changed")
    out = []
    out.append("RESULT: %d access removal(s), %d addition(s), %d change(s) documented."
               % (n_rem, n_add, n_chg))
    if n_add:
        out.append("        NOTE: additions are out of scope for an access-removal review. "
                   "Verify each one (see ACCESS ADDED in the report).")
    if exit_code == EXIT_WARNINGS:
        out.append("        %d integrity WARNING(s) need a human look - listed above and in the "
                   "report. Returning exit code 2." % len(findings.warnings))
    else:
        out.append("        No integrity warnings. Returning exit code 0.")
    out.append("Report: %s" % report_path)
    out.append("CSV:    %s" % csv_path)
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="access_diff.py",
        description="Human-readable diff of two SQL Server access-review JSON snapshots.",
        epilog="Exit codes: 0 ok, 1 could not run, 2 ran with integrity warnings.")
    p.add_argument("before", help="JSON collected BEFORE the permission changes")
    p.add_argument("after", help="JSON collected AFTER the permission changes")
    p.add_argument("--csv", metavar="FILE", help="CSV output path (default: next to AFTER)")
    p.add_argument("--report", metavar="FILE", help="text report path (default: next to AFTER)")
    p.add_argument("--allow-mismatch", action="store_true",
                   help="continue even if instance / environment / schema version differ")
    p.add_argument("--version", action="version", version="access_diff.py " + VERSION)
    return p.parse_args(argv)


def default_output_paths(after_path):
    folder = os.path.dirname(os.path.abspath(after_path))
    stem = os.path.basename(after_path)
    if stem.lower().endswith(".json"):
        stem = stem[:-5]
    return (os.path.join(folder, stem + ".access-diff.csv"),
            os.path.join(folder, stem + ".access-diff.txt"))


def run(argv):
    args = parse_args(argv)
    findings = Findings()

    before = Snapshot(args.before, "before", findings)
    after = Snapshot(args.after, "after", findings)
    check_compatibility(before, after, args.allow_mismatch, findings)

    section_names = list(SECTION_ORDER)
    for name in list(before.extra_sections) + list(after.extra_sections):
        if name not in section_names:
            section_names.append(name)
    results = [diff_section(name, before, after, findings) for name in section_names]

    exit_code = EXIT_WARNINGS if findings.warnings else EXIT_OK
    csv_default, report_default = default_output_paths(args.after)
    csv_path = os.path.abspath(args.csv or csv_default)
    report_path = os.path.abspath(args.report or report_default)

    generated = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    args_text = " ".join(argv)
    report = render_report(before, after, results, findings, args_text, generated)

    all_rows = []
    for res in results:
        all_rows.extend(res["rows"])
    all_rows.sort(key=lambda r: (group_sort_key(r["_group"]),
                                 {"Removed": 0, "Changed": 1, "Added": 2}[r["Change"]],
                                 row_sort_key(r)))
    try:
        write_csv(csv_path, all_rows)
        with open(report_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(report)
    except OSError as e:
        raise Fatal("could not write output: %s" % e)

    # Console: everything except the detail blocks when they are long.
    console = report
    detail_rows = sum(len(res["rows"]) for res in results)
    if detail_rows > 40:
        cut = report.find("ACCESS REMOVED\n")
        tail = report.find("SECTIONS WITH NO CHANGES\n")
        if cut != -1 and tail != -1:
            console = (report[:cut]
                       + "(%d detail lines omitted here - see the report file)\n\n" % detail_rows
                       + report[tail:])
    print(console, end="")
    print("\n".join(result_lines(results, findings, exit_code, csv_path, report_path)))
    return exit_code


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except Exception:
            pass
    try:
        code = run(sys.argv[1:])
    except Fatal as e:
        print("ERROR: %s" % e, file=sys.stderr)
        print("Nothing was written. Returning exit code 1.", file=sys.stderr)
        code = EXIT_ERROR
    except KeyboardInterrupt:
        print("Interrupted. Returning exit code 1.", file=sys.stderr)
        code = EXIT_ERROR
    sys.exit(code)


if __name__ == "__main__":
    main()
