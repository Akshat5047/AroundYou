# Around You

**Around You** is an AI-powered travel discovery and trip advisory web
application focused on **Telangana, India**.

It combines destination discovery, trip planning, budget estimation,
climate prediction, crowd insights, transport recommendations, review
trust analysis, cleanliness detection, Retrieval-Augmented Generation
(RAG), and Generative AI.

> **Important for Google AI Studio and automated coding tools:** This
> repository already contains an existing working application. **Do not
> rebuild, migrate, redesign, or replace the application architecture.
> Read this README before making changes.**

------------------------------------------------------------------------

## 1. Existing Architecture

``` text
User
  |
  v
Frontend (HTML + CSS + Vanilla JavaScript)
  |
  | REST API requests using fetch()
  v
FastAPI Backend
  |
  +-- Destination Service
  +-- Budget ML Model
  +-- Climate DL Model
  +-- Crowd ML Model
  +-- Transport ML Model
  +-- Review Trust NLP Model
  +-- Cleanliness YOLO Model
  +-- RAG System
  `-- AI Trip Planning Agent
       |
       +-------------------+
       |                   |
       v                   v
   Supabase              Gemini
   PostgreSQL            Generative AI
```

The frontend and backend are intentionally separate.

## 2. Frontend

The existing frontend uses **HTML, CSS, and Vanilla JavaScript**. It is
located in `/frontend`.

Main entry point:

``` text
/frontend/index.html
```

Major pages:

``` text
/frontend/index.html
/frontend/explore.html
/frontend/planner.html
/frontend/ask.html
/frontend/reviews.html
/frontend/cleanliness.html
```

Supporting resources:

``` text
/frontend/css/
/frontend/js/
/frontend/assets/
/frontend/data/
```

The frontend is already designed and functional.

**Do not convert it to React, Vite, Next.js, Tailwind, Angular, Vue, or
another framework unless explicitly requested by the project owner. Do
not regenerate the UI from datasets or backend endpoints.**

## 3. Backend

The backend is **Python + FastAPI** and is located in `/backend`.

Entry point:

``` text
/backend/main.py
```

The backend is already deployed on Render:

``` text
https://aroundyou-api-xi6n.onrender.com
```

Swagger/OpenAPI:

``` text
https://aroundyou-api-xi6n.onrender.com/docs
```

**Do not replace FastAPI with Express, Node.js, or another backend.**

## 4. Major API Endpoints

Existing endpoints include:

``` text
GET  /api/destinations
GET  /api/destinations?district=<district>
GET  /api/destinations/districts

POST /api/climate/predict
POST /api/reviews/classify
POST /api/cleanliness/analyze
POST /api/rag/ask
POST /api/agent/plan-trip
```

Inspect the existing backend routes and frontend JavaScript before
changing API behavior.

## 5. Destination Discovery

Explore lets users browse Telangana destinations and select multiple
places, including places from different districts.

Destination information includes fields such as name, district,
category, rating, popularity, entry fee, latitude, and longitude.

This is primarily data retrieval/recommendation support rather than a
separate ML model.

## 6. AI Trip Planner

The planner is an orchestration layer, not one ML model.

``` text
Trip Request
     |
     v
Trip Planning Agent
     |
     +-- RAG
     +-- Budget
     +-- Climate
     +-- Crowd
     `-- Transport
     |
     v
Collected Travel Context
     |
     v
Gemini
     |
     v
Final Trip Recommendation
```

Primary endpoint:

``` text
POST /api/agent/plan-trip
```

A deterministic fallback is available if the Generative AI call fails.

## 7. Budget Prediction

**Model:** XGBoost Multi-Output Regressor

The model predicts multiple trip cost components and the total estimated
trip cost. It is used for structured/tabular travel data in the Trip
Planner.

The lightweight Ask Around You Budget Advisor is separate from the full
ML prediction flow and provides budget allocation/advisory behavior
without fabricating missing ML inputs.

## 8. Climate Prediction

**Model:** LSTM (Long Short-Term Memory)

Originally trained with PyTorch and exported to ONNX for deployment.

Outputs include: - Maximum temperature - Minimum temperature - Rainfall
probability

Architecture:

``` text
Historical Climate Data -> Sequence Preparation -> LSTM -> ONNX -> FastAPI Prediction
```

## 9. Crowd Prediction

**Model:** Random Forest Regressor

The model estimates visitor footfall. Current predictions are
**month-level estimates**, not exact day-level predictions.

Season mapping:

``` text
December-February -> Winter
March-May         -> Summer
June-September    -> Monsoon
October-November  -> Post-Monsoon
```

## 10. Transport Recommendation

**Model:** Random Forest Classifier

Recommended modes include Car, Bus, Auto, and Bike. Project evaluation
produced approximately **95.5% accuracy**.

Ask Around You also contains a lightweight transport advisory. For
multiple destinations, latitude/longitude can be used with the Haversine
formula to calculate **straight-line geographic distance, not driving
distance**.

## 11. Review Trust Detection

**NLP Pipeline:** TF-IDF + Logistic Regression\
**Dataset:** Ott Deceptive Opinion Spam Corpus

``` text
Review Text -> Preprocessing -> TF-IDF -> Logistic Regression -> Confidence -> Genuine / Deceptive / Unverified
```

Project evaluation accuracy: approximately **91.25%**.

Confidence logic:

``` text
Confidence >= 70% -> Genuine / Deceptive
Confidence < 70%  -> Unverified
```

## 12. Cleanliness Analyzer

**Model:** YOLOv8n\
**Dataset:** TACO (Trash Annotations in Context)

Waste categories were collapsed into a general **Litter** class.

``` text
Uploaded Image -> YOLOv8n -> Litter Detection -> Cleanliness Analysis
```

Production deployment:

``` text
PyTorch .pt -> ONNX -> ONNX Runtime
```

## 13. Retrieval-Augmented Generation (RAG)

Around You includes grounded Telangana travel Q&A.

``` text
User Question
      |
      v
Embedding
      |
      v
Similarity Search
      |
      v
Relevant Telangana Travel Context
      |
      v
Context + Question
      |
      v
Gemini
      |
      v
Grounded Answer
```

The embedding system is based on a SentenceTransformer model exported to
ONNX.

**RAG retrieves the information; Gemini explains it.**

Endpoint:

``` text
POST /api/rag/ask
```

## 14. Ask Around You

Ask Around You is an interactive AI travel workspace.

Current tools: - Places to Visit - Budget Advisor - Weather - Crowd
Insights - Transport - Help Me Decide

Mapping:

``` text
Places to Visit -> RAG
Weather         -> LSTM Climate Model
Crowd Insights  -> Random Forest Regressor
Budget Advisor  -> Budget advisory logic
Transport       -> Distance + budget advisory
Help Me Decide  -> Multi-model comparison
```

## 15. Help Me Decide

This feature compares selected destinations using available factors such
as entry fee, predicted crowd, rainfall, maximum temperature, road
access when available, and available budget.

It uses deterministic multi-factor comparison logic based on existing
model outputs instead of training another unnecessary model.

## 16. Database

Around You uses **Supabase PostgreSQL** for cloud persistence.

Important tables include:

``` text
trip_requests
trip_results
```

Local tourism data / SQLite is also used where appropriate for
destination information and supporting data.

## 17. Technology Stack

  Area                 Technology
  -------------------- -----------------------------------------
  Frontend             HTML, CSS, Vanilla JavaScript
  Backend              Python, FastAPI
  Budget               XGBoost Multi-Output Regression
  Climate              LSTM, PyTorch, ONNX
  Crowd                Random Forest Regression
  Transport            Random Forest Classification
  Reviews              TF-IDF + Logistic Regression
  Cleanliness          YOLOv8n + ONNX Runtime
  RAG                  SentenceTransformer embeddings + Gemini
  Generative AI        Gemini
  Cloud Database       Supabase PostgreSQL
  Local Data           SQLite / datasets
  Backend Deployment   Render
  Version Control      Git + GitHub

## 18. Local Development

### Backend

``` powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Local backend: `http://127.0.0.1:8000`\
Swagger: `http://127.0.0.1:8000/docs`

### Frontend

``` powershell
cd frontend
python -m http.server 5500
```

Local frontend: `http://localhost:5500`

## 19. IMPORTANT: Rules for Google AI Studio / Automated Coding Tools

### Goal

If this repository is imported into Google AI Studio, the goal is:

> **Run and/or publish the existing vanilla HTML/CSS/JavaScript frontend
> while preserving the externally deployed FastAPI backend and all
> existing functionality.**

Production API:

``` text
https://aroundyou-api-xi6n.onrender.com
```

### DO

-   Read this README first.
-   Treat `/frontend/index.html` as the main frontend entry point.
-   Preserve all existing HTML pages.
-   Preserve existing CSS and JavaScript.
-   Preserve existing navigation and REST API calls.
-   Continue using the externally deployed FastAPI backend.
-   Make only the minimum configuration changes needed to run or publish
    the existing frontend.
-   Inspect existing files before creating replacements.

### DO NOT

-   Do not rebuild Around You from scratch.
-   Do not convert the frontend to React.
-   Do not convert the frontend to Vite.
-   Do not replace existing CSS with Tailwind.
-   Do not replace FastAPI with Express or Node.js.
-   Do not create a new backend.
-   Do not create new ML models from datasets in this repository.
-   Do not retrain models.
-   Do not replace existing API endpoints.
-   Do not generate a new application based on one dataset or one
    backend route.
-   Do not redesign the existing UI unless explicitly requested.
-   Do not remove existing pages or features.
-   Do not modify production API behavior merely to fit a generated
    frontend.

If AI Studio requires a small Node-based development server or
configuration **solely to serve the existing static frontend in its
preview environment**, it may add the minimum wrapper/configuration
necessary. It must **not migrate the application itself to React/Express
or replace the existing architecture**.

## 20. Security

Secrets and environment variables must not be committed to Git.

Files such as `.env`, virtual environments, credentials, API keys, and
sensitive configuration should remain excluded through `.gitignore`.

Never hard-code private API keys into frontend JavaScript.

## 21. Current Status

-   FastAPI backend: **Deployed on Render**
-   ML/DL/NLP/CV inference endpoints: **Integrated**
-   RAG: **Integrated**
-   AI Trip Planning Agent: **Integrated**
-   Supabase persistence: **Integrated**
-   Existing frontend: **Functional**
-   Final public frontend production deployment: **Being finalized**

## 22. Key Architectural Principle

Around You deliberately uses a **multi-model architecture**:

-   Structured prediction -\> XGBoost / Random Forest
-   Time-series forecasting -\> LSTM
-   Text classification -\> TF-IDF + Logistic Regression
-   Object detection -\> YOLOv8n
-   Knowledge retrieval -\> RAG / embeddings
-   Natural-language synthesis and trip orchestration -\> Gemini + AI
    Agent

Different tasks have different data structures and objectives. The
system combines specialized models through FastAPI rather than forcing
every problem through one model.
