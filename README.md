# StratosPic

**Cloud-deployed Python photo-sharing application with automated image analysis and NLP-based comment sentiment filtering.**

StratosPic is a portfolio project demonstrating how application engineering, cloud services and lightweight AI/NLP components can be combined in a production-style Python web application.

It is intentionally positioned as a **cloud/application engineering project that supports an AI/ML portfolio** rather than as a deep computer-vision model.

## What the application does

- User registration and authentication
- Creator and consumer roles
- Photo upload and profile management
- Feed search, likes, saves and comments
- Azure Blob Storage integration with local-development fallback
- PostgreSQL support with SQLite fallback for development
- Rule-based image metadata analysis with Pillow
- TextBlob sentiment scoring for comment moderation
- Health endpoint for deployment checks
- Docker support
- GitHub Actions CI
- Optional Azure App Service deployment workflow

## Technology stack

| Area | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL, SQLAlchemy |
| Authentication | Flask-Login |
| Security | Flask-WTF CSRF protection, secure cookies, upload validation |
| Media | Pillow |
| NLP | TextBlob sentiment analysis |
| Storage | Azure Blob Storage |
| Cloud | Microsoft Azure App Service |
| Containerisation | Docker |
| CI | GitHub Actions |
| Production server | Gunicorn |

## Architecture

```text
Browser
   |
   v
Flask application
   |---- Authentication / profiles
   |---- Feed / likes / saves / comments
   |---- Rule-based image analysis
   |---- TextBlob sentiment scoring
   |
   +---- SQLAlchemy ----> PostgreSQL
   |
   +---- Media storage -> Azure Blob Storage

GitHub Actions
   |
   +---- dependency installation
   +---- automated tests
   +---- Docker build validation

Manual deployment workflow
   |
   +---- Azure OIDC login
   +---- Azure App Service
```

## AI / automation scope

### Image analysis

The upload pipeline uses Pillow to calculate deterministic metadata such as:

- image resolution category;
- brightness;
- dominant colour tone.

This is **rule-based image analysis**, not a trained computer-vision model.

### Comment sentiment

Comments are scored with TextBlob polarity. Strongly negative comments can be rejected by a simple moderation rule.

TextBlob is used here as a lightweight NLP component. It is not presented as a modern transformer-based moderation system.

## Security improvements

The portfolio-hardened version includes:

- no public hard-coded production secret;
- mandatory `SECRET_KEY` when `APP_ENV=production`;
- CSRF protection for state-changing requests;
- HTTP-only and secure production cookies;
- image extension and content validation;
- upload size limits;
- image pixel limits;
- randomized stored filenames;
- production-disabled debug endpoint;
- basic password-length and input validation.

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/minhajul-abedin-ai/StratosPic.git
cd StratosPic
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure development environment

Create a `.env` file:

```env
APP_ENV=development
SECRET_KEY=replace-this-with-a-random-secret
DATABASE_URL=sqlite:///instance/app.db
```

Azure storage is optional during local development.

### 5. Run

```bash
flask --app app run
```

or:

```bash
python app.py
```

## Docker

Build:

```bash
docker build -t stratospic .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e SECRET_KEY="replace-with-a-secure-secret" \
  stratospic
```

For persistent production data, also configure PostgreSQL and Azure Blob Storage.

## Tests

```bash
pytest -q
```

CI runs the test suite and validates the Docker build on pushes and pull requests.

## Azure deployment

The repository contains an Azure App Service deployment workflow.

Deployment is **manual by design** because Azure OIDC credentials are environment-specific. The previous automatic deployment had a successful build but later failed at the Azure login step after the Azure credentials/configuration stopped validating.

Before deploying, configure or refresh these repository secrets:

- Azure client ID
- Azure tenant ID
- Azure subscription ID

Then run the deployment workflow manually from GitHub Actions.

## Production environment variables

| Variable | Purpose |
|---|---|
| `APP_ENV=production` | Enables production security behaviour |
| `SECRET_KEY` | Flask session/CSRF secret |
| `DATABASE_URL` or `AZURE_POSTGRESQL_CONNECTIONSTRING` | Persistent database |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob Storage credentials |
| `AZURE_CONTAINER_NAME` | Blob container name |
| `MAX_UPLOAD_BYTES` | Optional upload-size override |
| `MAX_IMAGE_PIXELS` | Optional image pixel-limit override |

## Portfolio value

StratosPic demonstrates that I can work beyond model experimentation and integrate software engineering around AI-related components:

- Flask application development
- authentication and data modelling
- PostgreSQL integration
- cloud object storage
- containerisation
- CI/CD
- security hardening
- NLP component integration
- deployment-oriented engineering

For deeper machine-learning and explainable-AI work, see my other projects on my [GitHub profile](https://github.com/minhajul-abedin-ai).

## Author

**Minhajul Abedin**  
AI / Machine Learning Engineer  
London, United Kingdom

[GitHub](https://github.com/minhajul-abedin-ai) · [LinkedIn](https://www.linkedin.com/in/minhajulabedinai)
