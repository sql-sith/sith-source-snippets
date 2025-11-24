# URI Type Hierarchy


```plaintext
URI
├─ URL (locator)
│  ├─ Hierarchical form (uses //authority)
│  │  ├─ http / https    → scheme://authority/path?query#fragment
│  │  ├─ ftp             → scheme://authority/path
│  │  ├─ file            → scheme://authority/path
│  │  ├─ ws / wss        → scheme://authority/path
│  │  ├─ ssh             → scheme://authority/path
│  │  └─ git             → scheme://authority/path
│  └─ Non-hierarchical URL variants (rare)
│     └─ (protocols that locate but don’t use // in practice)
│
└─ Non-URL URIs
   ├─ URN (name)
   │  └─ urn:isbn:0451450523         → scheme:opaque-part
   └─ Other opaque schemes
      ├─ mailto:someone@example.com  → scheme:opaque-part
      ├─ tel:+1-800-555-1234         → scheme:opaque-part
      ├─ data:text/plain;base64,...  → scheme:opaque-part
      └─ sip:alice@atlanta.com       → scheme:opaque-part
```

## Quick explanation of the branches

- **URI** is the umbrella term for any identifier.
- **URL** is a subtype of URI that names and tells you *how to locate* a resource. Most URLs are **hierarchical** and follow a `scheme://authority/path/?query#fragment` syntax, though certain elements are frequently omitted. For example, file URLs like `file:///path` have only a scheme and path.
- **URN** and other **opaque** schemes are URIs that *name* or *embed* data but do not give information on how to locate it elsewhere on the network. They use `scheme:scheme-specific-part` and do not decompose into the `scheme://authority/path/?query#fragment` syntax.
