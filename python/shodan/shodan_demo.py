import shodan

API_KEY = "YOUR_API_KEY"
api = shodan.Shodan(API_KEY)

# Search for Apache servers
results = api.search("apache")

print(f"Results found: {results['total']}")
for result in results['matches']:
    print(f"IP: {result['ip_str']}")
    print(f"Port: {result['port']}")
    print(f"Data: {result['data']}")

    print("-" * 40)

