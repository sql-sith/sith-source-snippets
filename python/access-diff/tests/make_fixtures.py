#!/usr/bin/env python3
"""
make_fixtures.py - build a before/after test pair from one real collector file.

    python3 make_fixtures.py SOURCE.json OUT_DIR

Writes into OUT_DIR:
    clean_before.json      SOURCE with misfiled records put back and dangling refs dropped
    clean_after.json       clean_before with a known set of edits (listed in EXPECTED.txt)
    same_after.json        clean_before with only CollectedAtUtc bumped (expect zero changes)
    other_instance.json    clean_before with a different InstanceGuid (expect exit 1)
    broken.json            not JSON (expect exit 1)
    EXPECTED.txt           what access_diff.py should report for clean_before vs clean_after

The fixtures are derived from real data. Do not ship them with the tool.
"""
import copy
import json
import os
import sys


def classify_misfiled(data):
    """Move Users found in Principals, and AdGroupMemberships found in AdAccounts."""
    moved = 0
    keep = []
    for rec in data.get("Principals", []):
        if "UserGuid" in rec:
            data.setdefault("Users", []).append(rec)
            moved += 1
        else:
            keep.append(rec)
    data["Principals"] = keep
    keep = []
    for rec in data.get("AdAccounts", []):
        if "IsDirect" in rec and "LoginName" not in rec:
            data.setdefault("AdGroupMemberships", []).append(rec)
            moved += 1
        else:
            keep.append(rec)
    data["AdAccounts"] = keep
    data.setdefault("AdGroupMemberships", [])
    data.setdefault("AdGroups", [])
    return moved


def drop_dangling(data):
    acct = {r["AdAccountGuid"] for r in data["AdAccounts"]}
    before = len(data["AdGroupMemberships"])
    data["AdGroupMemberships"] = [m for m in data["AdGroupMemberships"] if m["AdAccountGuid"] in acct]
    return before - len(data["AdGroupMemberships"])


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    with open(src, encoding="utf-8-sig") as fh:
        base = json.load(fh)

    moved = classify_misfiled(base)
    dropped = drop_dangling(base)
    print("fixture base: moved %d misfiled records, dropped %d dangling memberships" % (moved, dropped))

    dbname = {d["DatabaseGuid"]: d["Name"] for d in base["Databases"]}
    users = {u["UserGuid"]: u for u in base["Users"]}
    roles = {r["RoleGuid"]: r for r in base["Roles"]}

    def grantee(g):
        if g["UserGuid"]:
            return users[g["UserGuid"]]["Name"]
        return roles[g["RoleGuid"]]["Name"]

    after = copy.deepcopy(base)
    after["Collection"]["CollectedAtUtc"] = "2026-11-20T03:15:00.0000000"
    after["Collection"]["CollectedByLogin"] = "CORP\\reviewer"
    expected = []
    touched_users = set()   # grantees of grants edited in steps 1-5; step 6 must not drop them

    # 1. Partial revoke, same GrantGuid: a multi-permission DML grant loses one permission.
    g = next(x for x in after["Grants"] if x["Description"] == "DELETE, INSERT, UPDATE")
    g["Description"] = "INSERT, UPDATE"
    touched_users.add(g["UserGuid"])
    expected.append("CHANGED  Grants  %s / %s: DELETE revoked (DELETE, INSERT, UPDATE -> INSERT, UPDATE), same GrantGuid %s"
                    % (dbname[g["DatabaseGuid"]], grantee(g), g["GrantGuid"]))

    # 2. Partial revoke, NEW GrantGuid (collector re-minted it): should still pair by slot.
    g = next(x for x in after["Grants"] if x["Description"] == "DELETE, INSERT" and x is not g)
    old = g["GrantGuid"]
    g["GrantGuid"] = "11111111-2222-3333-4444-555555555555"
    g["Description"] = "INSERT"
    touched_users.add(g["UserGuid"])
    expected.append("CHANGED  Grants  %s / %s: DELETE revoked (DELETE, INSERT -> INSERT), GrantGuid re-minted %s -> %s (expect a NOTE, not Removed+Added)"
                    % (dbname[g["DatabaseGuid"]], grantee(g), old, g["GrantGuid"]))

    # 3. WITH GRANT OPTION turned off on an otherwise unchanged grant.
    g = next(x for x in after["Grants"] if x["Description"] == "SELECT" and x["Scope"] == "OBJECT" and not x["WithGrantOption"])
    base_g = next(x for x in base["Grants"] if x["GrantGuid"] == g["GrantGuid"])
    base_g["WithGrantOption"] = True   # make BEFORE have it on, AFTER off
    touched_users.add(g["UserGuid"])
    expected.append("CHANGED  Grants  %s / %s: WithGrantOption true -> false, GrantGuid %s"
                    % (dbname[g["DatabaseGuid"]], grantee(g), g["GrantGuid"]))

    # 4. A DENY removed (increases access - should be called out).
    g = next(x for x in after["Grants"] if x["GrantType"] == "DENY")
    after["Grants"].remove(g)
    expected.append("REMOVED  Grants  DENY of %s on %s in %s removed, GrantGuid %s (sentence should warn access increased)"
                    % (g["Description"], grantee(g), dbname[g["DatabaseGuid"]], g["GrantGuid"]))

    # 5. A grant added (out of scope, should land in ACCESS ADDED).
    g = copy.deepcopy(next(x for x in after["Grants"] if x["Description"] == "EXECUTE" and x["UserGuid"]))
    g["GrantGuid"] = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
    g["Description"] = "CONTROL"
    g["GrantType"] = "OTHER"
    g["Scope"] = "DATABASE"
    g["ObjCount"] = 1
    g["ExecDetail"] = None
    after["Grants"].append(g)
    touched_users.add(g["UserGuid"])
    expected.append("ADDED    Grants  %s / %s: CONTROL granted, GrantGuid %s"
                    % (dbname[g["DatabaseGuid"]], grantee(g), g["GrantGuid"]))

    # 6. A whole user dropped from one database: user, its memberships, its grants all vanish.
    cands = [u for u in after["Users"] if u["TypeDesc"] == "WINDOWS_GROUP"
             and u["UserGuid"] not in touched_users
             and any(m["MemberGuid"] == u["UserGuid"] for m in after["RoleMemberships"])
             and any(x["UserGuid"] == u["UserGuid"] for x in after["Grants"])]
    u = cands[0]
    n_mem = sum(1 for m in after["RoleMemberships"] if m["MemberGuid"] == u["UserGuid"])
    n_gr = sum(1 for x in after["Grants"] if x["UserGuid"] == u["UserGuid"])
    after["Users"].remove(u)
    after["RoleMemberships"] = [m for m in after["RoleMemberships"] if m["MemberGuid"] != u["UserGuid"]]
    after["Grants"] = [x for x in after["Grants"] if x["UserGuid"] != u["UserGuid"]]
    expected.append("REMOVED  Users+RoleMemberships+Grants  %s dropped from %s: 1 user, %d membership(s), %d grant(s) = %d rows, UserGuid %s"
                    % (u["Name"], dbname[u["DatabaseGuid"]], n_mem, n_gr, 1 + n_mem + n_gr, u["UserGuid"]))

    # 7. One role membership removed, user kept.
    m = next(x for x in after["RoleMemberships"] if x["MemberType"] == "USER"
             and roles[x["RoleGuid"]]["Name"] == "db_owner")
    after["RoleMemberships"].remove(m)
    expected.append("REMOVED  RoleMemberships  %s removed from db_owner in %s, RoleMembershipGuid %s"
                    % (users[m["MemberGuid"]]["Name"], dbname[m["DatabaseGuid"]], m["RoleMembershipGuid"]))

    # 8. A server login dropped (Principals).
    p = next(x for x in after["Principals"] if x["TypeDesc"] == "WINDOWS_LOGIN"
             and not any(a["PrincipalGuid"] == x["PrincipalGuid"] for a in after["AdAccounts"])
             and not any(gm["PrincipalGuid"] == x["PrincipalGuid"] for gm in after["AdGroupMemberships"]))
    after["Principals"].remove(p)
    expected.append("REMOVED  Principals  login %s removed from server, PrincipalGuid %s" % (p["Name"], p["PrincipalGuid"]))

    # 9. An AD account disabled (Enabled flag), still present.
    a = next(x for x in after["AdAccounts"] if x["Enabled"])
    a["Enabled"] = False
    expected.append("CHANGED  AdAccounts  %s Enabled true -> false, AdAccountGuid %s" % (a["LoginName"], a["AdAccountGuid"]))

    # 10. A user whose UserGuid was re-minted but nothing else changed: should match by name, warn, no change rows.
    u2 = next(x for x in after["Users"] if x["Name"] == "dbo")
    old = u2["UserGuid"]
    u2["UserGuid"] = "99999999-8888-7777-6666-555555555555"
    for m in after["RoleMemberships"]:
        if m["MemberGuid"] == old:
            m["MemberGuid"] = u2["UserGuid"]
    for x in after["Grants"]:
        if x["UserGuid"] == old:
            x["UserGuid"] = u2["UserGuid"]
    expected.append("WARNING  Users  dbo in %s has a new UserGuid (%s -> %s): expect a 'match by name' WARNING, zero change rows for it"
                    % (dbname[u2["DatabaseGuid"]], old, u2["UserGuid"]))

    # Noise that must NOT be reported: timestamp drift, derived stats.
    after["Principals"][0]["CreateDate"] = "1999-01-01T00:00:00.000"
    for x in after["Grants"]:
        if x.get("ExecDetail"):
            x["ExecDetail"]["RO"] = 999
            break
    expected.append("SILENT   CreateDate drift on Principals[0] and ExecDetail.RO change on one grant must not appear")

    def dump(name, obj):
        with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True)

    dump("clean_before.json", base)
    dump("clean_after.json", after)

    same = copy.deepcopy(base)
    same["Collection"]["CollectedAtUtc"] = "2026-11-20T03:15:00.0000000"
    dump("same_after.json", same)

    other = copy.deepcopy(same)
    other["Instance"]["InstanceGuid"] = "00000000-0000-0000-0000-000000000000"
    other["Instance"]["ServerName"] = "SOMEOTHERBOX"
    dump("other_instance.json", other)

    with open(os.path.join(out, "broken.json"), "w") as fh:
        fh.write('{"this is": not json')

    with open(os.path.join(out, "EXPECTED.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(expected) + "\n")
    print("\n".join(expected))

    # Machine-checkable expectations for run_tests.py.
    counts = {
        "Principals": {"Removed": 1},
        "Users": {"Removed": 1},
        "RoleMemberships": {"Removed": 1 + n_mem},
        "Grants": {"Removed": 1 + n_gr, "Added": 1, "Changed": 3},
        "AdAccounts": {"Changed": 1},
    }
    must_contain = [
        "revoked: DELETE",
        "WITH GRANT OPTION on SELECT",
        "removing a DENY increases access",
        "CONTROL (database scope) was granted",
        "%s was removed from database %s" % (u["Name"], dbname[u["DatabaseGuid"]]),
        "was removed from role db_owner",
        "Login %s was removed from the server" % p["Name"],
        "Enabled changed from true to false (account disabled)",
        "match by name but carry a different UserGuid",
        "only grant in that slot on both sides",
        "11111111-2222-3333-4444-555555555555",
    ]
    must_not_contain = ["1999-01-01", "ExecDetail", "CreateDate"]
    with open(os.path.join(out, "expected.json"), "w", encoding="utf-8") as fh:
        json.dump({"counts": counts, "must_contain": must_contain,
                   "must_not_contain": must_not_contain,
                   "dropped_user_guid": u["UserGuid"],
                   "dropped_user_rows": 1 + n_mem + n_gr}, fh, indent=2)


if __name__ == "__main__":
    main()
