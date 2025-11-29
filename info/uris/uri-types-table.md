# Examples of Common URI Schemes

---

<h2>Examples of Common Schemes</h2>

<table border="1" cellpadding="6" cellspacing="0" style="width: 100%" >
    <colgroup>
      <col width="1%">
      <col width="1%">
      <col width="96%">
      <col width="1%">
      <col witdh="1%">
      <col width="1%">
  </colgroup>
  <tr>
    <th>Scheme</th>
    <th>Type</th>
    <th>Syntax</th>
    <th>Example</th>
    <th>Breakdown</th>
    <th>Notes</th>
  </tr>
  <tr>
    <td>http / https</td>
    <td>URL</td>
    <td>scheme://authority/path?query#fragment</td>
    <td><code>https://example.com/page?x=1#top</code></td>
    <td>
      scheme = https<br>
      authority = example.com<br>
      path = /page<br>
      query = x=1<br>
      fragment = top
    </td>
    <td>Most common; locates web resources over HTTP(S).</td>
  </tr>
  <tr>
    <td>ftp</td>
    <td>URL</td>
    <td>scheme://authority/path</td>
    <td>ftp://ftp.gnu.org/gnu/</td>
    <td>
      scheme = ftp<br>
      authority = ftp.gnu.org<br>
      path = /gnu/
    </td>
    <td>File Transfer Protocol; less common today.</td>
  </tr>
  <tr>
    <td>file</td>
    <td>URL</td>
    <td>scheme://authority/path</td>
    <td>file:///C:/Users/Chris/document.txt</td>
    <td>
      scheme = file<br>
      authority = (empty)<br>
      path = /C:/Users/Chris/document.txt
    </td>
    <td>Local filesystem resource.</td>
  </tr>
  <tr>
    <td>ws / wss</td>
    <td>URL</td>
    <td>scheme://authority/path</td>
    <td>wss://example.com/socket</td>
    <td>
      scheme = wss<br>
      authority = example.com<br>
      path = /socket
    </td>
    <td>WebSocket connections (secure and insecure).</td>
  </tr>
  <tr>
    <td>ssh</td>
    <td>URL</td>
    <td>scheme://authority/path</td>
    <td>ssh://user@host:22/</td>
    <td>
      scheme = ssh<br>
      authority = user@host:22<br>
      path = /
    </td>
    <td>Secure shell access.</td>
  </tr>
  <tr>
    <td>git</td>
    <td>URL</td>
    <td>scheme://authority/path</td>
    <td>git://github.com/user/repo.git</td>
    <td>
      scheme = git<br>
      authority = github.com<br>
      path = /user/repo.git
    </td>
    <td>Git transport protocol.</td>
  </tr>
  <tr>
    <td>mailto</td>
    <td>URI (not URL)</td>
    <td>scheme:opaque-part</td>
    <td>mailto:someone@example.com</td>
    <td>
      scheme = mailto<br>
      opaque part = someone@example.com
    </td>
    <td>Identifies an email address; doesn’t fetch content.</td>
  </tr>
  <tr>
    <td>tel</td>
    <td>URI (not URL)</td>
    <td>scheme:opaque-part</td>
    <td>tel:+1-800-555-1234</td>
    <td>
      scheme = tel<br>
      opaque part = +1-800-555-1234
    </td>
    <td>Identifies a phone number.</td>
  </tr>
  <tr>
    <td>urn</td>
    <td>URN</td>
    <td>scheme:opaque-part</td>
    <td>urn:isbn:0451450523</td>
    <td>
      scheme = urn<br>
      opaque part = isbn:0451450523
    </td>
    <td>Persistent name (ISBN, UUID, etc.), no location.</td>
  </tr>
  <tr>
    <td>data</td>
    <td>URI</td>
    <td>scheme:opaque-part</td>
    <td>data:text/plain;base64,SGVsbG8=</td>
    <td>
      scheme = data<br>
      opaque part = text/plain;base64,SGVsbG8=
    </td>
    <td>Embeds data directly in the URI.</td>
  </tr>
  <tr>
    <td>sip</td>
    <td>URI</td>
    <td>scheme:opaque-part</td>
    <td>sip:alice@atlanta.com</td>
    <td>
      scheme = sip<br>
      opaque part = alice@atlanta.com
    </td>
    <td>Session Initiation Protocol (VoIP).</td>
  </tr>
</table>
