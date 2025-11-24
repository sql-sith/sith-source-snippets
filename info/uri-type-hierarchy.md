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
   │  └─ urn:isbn:0451450523    → scheme:opaque-part
   └─ Other opaque schemes
      ├─ mailto:someone@example.com  → scheme:opaque-part
      ├─ tel:+1-800-555-1234        → scheme:opaque-part
      ├─ data:text/plain;base64,... → scheme:opaque-part
      └─ sip:alice@atlanta.com      → scheme:opaque-part
```
