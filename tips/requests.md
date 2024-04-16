# Speed up the Python `requests` module

If you want to use the `requests` module for many fast requests one after each other, use a session:

```python
import requests

# The session will keep the connection open and reduce the times around 15x
session = requests.Session()
for _ in range(10):
    session.get("https://www.example.com")
```

For more information and the source,
visit [StackOverflow](https://stackoverflow.com/questions/62599036/python-requests-is-slow-and-takes-very-long-to-complete-http-or-https-request). 
