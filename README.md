# Operations API (Python)

Sample backend used to exercise Dev CI/CD on GitHub Actions.

- Domain: products, customers, inventory, orders, money
- Services: pricing, inventory, orders, auth
- Tests: pytest (run locally with `python -m pytest`)

Dev pipeline: merge to `dev` → tests → build Function + App Service packages → simulated Azure deploy.
