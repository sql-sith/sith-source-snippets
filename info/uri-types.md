# Examples of Common URI Schemes

---

| **Scheme**       | **Type**       | **Example**                           | **Syntax**                               | **Breakdown**                                                                                        | **Notes**                                      |
| ---------------- | -------------- | ------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `http`/`https`   | URL            | `https://example.com/page?x=1#top`    | `scheme://authority/path?query#fragment` | scheme = https<br>authority = example.com<br>path = /page<br>query = x=1<br>fragment = top | Most common; locates web resources over HTTP(S).     |
| `ftp`            | URL            | `ftp://ftp.gnu.org/gnu/`              | `scheme://authority/path`                | scheme = ftp<br>authority = ftp.gnu.org<br>path = /gnu/                                            | File Transfer Protocol; less common today.           |
| `file`           | URL            | `file:///C:/Users/Chris/document.txt` | `scheme://authority/path`                | scheme = file<br>authority = (empty)<br>path = /C:/Users/Chris/document.txt                        | Local filesystem resource.                           |
| `ws`/`wss`       | URL            | `wss://example.com/socket`            | `scheme://authority/path`                | scheme = wss<br>authority = example.com<br>path = /socket                                          | WebSocket connections (secure and insecure).         |
| `ssh`            | URL            | `ssh://user@host:22/`                 | `scheme://authority/path`                | scheme = ssh<br>authority = user@host:22<br>path = /                                               | Secure shell access.                                 |
| `git`            | URL            | `git://github.com/user/repo.git`      | `scheme://authority/path`                | scheme = git<br>authority = github.com<br>path = /user/repo.git                                    | Git transport protocol.                              |
| `mailto`         | URI (not URL)  | `mailto:someone@example.com`          | `scheme:opaque-part`                     | scheme = mailto<br>opaque part = someone@example.com                                                   | Identifies an email address; doesn’t fetch content. |
| `tel`            | URI (not URL)  | `tel:+1-800-555-1234`                 | `scheme:opaque-part`                     | scheme = tel<br>opaque part = +1-800-555-1234                                                          | Identifies a phone number.                           |
| `urn`            | URN            | `urn:isbn:0451450523`                 | `scheme:opaque-part`                     | scheme = urn<br>opaque part = isbn:0451450523                                                          | Persistent name (ISBN, UUID, etc.), no location.     |
| `data`           | URI            | `data:text/plain;base64,SGVsbG8=`     | `scheme:opaque-part`                     | scheme = data<br>opaque part = text/plain;base64,SGVsbG8=                                              | Embeds data directly in the URI.                     |
| `sip`            | URI            | `sip:alice@atlanta.com`               | `scheme:opaque-part`                     | scheme = sip<br>opaque part = alice@atlanta.com                                                        | Session Initiation Protocol (VoIP).                  |

---

<table>
<thead>
<tr><th><strong>Scheme</strong></th><th><strong>Type</strong></th><th><strong>Example</strong></th><th><strong>Syntax</strong></th><th><strong>Breakdown</strong></th><th><strong>Notes</strong></th></tr>
</thead>
<tbody>
<tr><td><code>http</code> / <code>https</code></td><td>URL</td><td><code>https://example.com/page?x=1#top</code></td><td><code>scheme://authority/path?query#fragment</code></td><td>scheme = https&lt;br&gt;authority = example.com&lt;br&gt;path = /page&lt;br&gt;query = x=1&lt;br&gt;fragment = top</td><td>Most common; locates web resources over HTTP(S).</td></tr>
<tr><td><code>ftp</code></td><td>URL</td><td><code>ftp://ftp.gnu.org/gnu/</code></td><td><code>scheme://authority/path</code></td><td>scheme = ftp&lt;br&gt;authority = ftp.gnu.org&lt;br&gt;path = /gnu/</td><td>File Transfer Protocol; less common today.</td></tr>
<tr><td><code>file</code></td><td>URL</td><td><code>file:///C:/Users/Chris/document.txt</code></td><td><code>scheme://authority/path</code></td><td>scheme = file&lt;br&gt;authority = (empty)&lt;br&gt;path = /C:/Users/Chris/document.txt</td><td>Local filesystem resource.</td></tr>
<tr><td><code>ws</code> / <code>wss</code></td><td>URL</td><td><code>wss://example.com/socket</code></td><td><code>scheme://authority/path</code></td><td>scheme = wss&lt;br&gt;authority = example.com&lt;br&gt;path = /socket</td><td>WebSocket connections (secure and insecure).</td></tr>
<tr><td><code>ssh</code></td><td>URL</td><td><code>ssh://user@host:22/</code></td><td><code>scheme://authority/path</code></td><td>scheme = ssh&lt;br&gt;authority = user@host:22&lt;br&gt;path = /</td><td>Secure shell access.</td></tr>
<tr><td><code>git</code></td><td>URL</td><td><code>git://github.com/user/repo.git</code></td><td><code>scheme://authority/path</code></td><td>scheme = git&lt;br&gt;authority = github.com&lt;br&gt;path = /user/repo.git</td><td>Git transport protocol.</td></tr>
<tr><td><code>mailto</code></td><td>URI (not URL)</td><td><code>mailto:someone@example.com</code></td><td><code>scheme:opaque-part</code></td><td>scheme = mailto&lt;br&gt;opaque part = someone@example.com</td><td>Identifies an email address; doesn’t fetch content.</td></tr>
<tr><td><code>tel</code></td><td>URI (not URL)</td><td><code>tel:+1-800-555-1234</code></td><td><code>scheme:opaque-part</code></td><td>scheme = tel&lt;br&gt;opaque part = +1-800-555-1234</td><td>Identifies a phone number.</td></tr>
<tr><td><code>urn</code></td><td>URN</td><td><code>urn:isbn:0451450523</code></td><td><code>scheme:opaque-part</code></td><td>scheme = urn&lt;br&gt;opaque part = isbn:0451450523</td><td>Persistent name (ISBN, UUID, etc.), no location.</td></tr>
<tr><td><code>data</code></td><td>URI</td><td><code>data:text/plain;base64,SGVsbG8=</code></td><td><code>scheme:opaque-part</code></td><td>scheme = data&lt;br&gt;opaque part = text/plain;base64,SGVsbG8=</td><td>Embeds data directly in the URI.</td></tr>
<tr><td><code>sip</code></td><td>URI</td><td><code>sip:alice@atlanta.com</code></td><td><code>scheme:opaque-part</code></td><td>scheme = sip&lt;br&gt;<br/>opaque part = alice@atlanta.com</td><td>Session Initiation Protocol (VoIP).</td></tr>
</tbody>
</table>
This way you can show both the **concise syntax form** and the **expanded breakdown** side by side.

Would you like me to also add a **visual diagram/tree** (URI → URL vs. URN → hierarchical vs. opaque schemes) so you have both a tabular and a graphical artifact for teaching?
