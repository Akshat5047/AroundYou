# Around You

> **An AI-Powered Travel Discovery and Trip Advisory Platform for
> Telangana**

Around You is an intelligent travel assistance platform designed to
bring destination discovery, trip planning, travel predictions, review
intelligence, cleanliness analysis, and AI-powered guidance into one
connected application.

Instead of relying on separate applications for weather, budgeting,
crowd information, reviews, transport, and itinerary planning, Around
You integrates **Machine Learning, Deep Learning, Natural Language
Processing, Computer Vision, Retrieval-Augmented Generation (RAG), and
Generative AI** through a unified FastAPI backend.

------------------------------------------------------------------------

## Table of Contents

-   [Project Overview](#project-overview)
-   [Problem Statement](#problem-statement)
-   [Objectives](#objectives)
-   [Key Features](#key-features)
-   [System Architecture](#system-architecture)
-   [AI and Machine Learning
    Components](#ai-and-machine-learning-components)
-   [Technology Stack](#technology-stack)
-   [Project Structure](#project-structure)
-   [API Overview](#api-overview)
-   [Database](#database)
-   [Installation and Local Setup](#installation-and-local-setup)
-   [Deployment](#deployment)
-   [Current Status](#current-status)
-   [Future Scope](#future-scope)
-   [Academic Note](#academic-note)

------------------------------------------------------------------------

## Project Overview

Travelers in unfamiliar locations often need to combine information from
multiple disconnected sources before making travel decisions.
Destination information, weather conditions, budget estimates, crowd
levels, transport options, reviews, and itinerary planning may all come
from different applications.

**Around You** addresses this problem by providing an integrated travel
advisory system focused on **Telangana, India**.

The platform uses different specialized AI models for different tasks
rather than depending on a single model for every feature. These models
are exposed through a **FastAPI REST backend** and consumed by a web
frontend built using **HTML, CSS, and JavaScript**.

### Domain

**Travel Discovery & Trip Advisory**

### Geographic Scope

**Telangana, India**

------------------------------------------------------------------------

## Problem Statement

Travelers currently face decision paralysis because useful travel
information is fragmented across weather applications, budget tools,
travel blogs, review platforms, and navigation services.

Generic travel recommendations may not consider important factors such
as changing climate conditions, expected visitor footfall, available
budget, transportation requirements, destination cleanliness, or the
reliability of online reviews.

Around You aims to reduce this fragmentation by providing a single
intelligent platform that combines destination discovery with predictive
models and AI-assisted trip planning.

------------------------------------------------------------------------

## Objectives

The main objectives of Around You are to:

-   Provide centralized discovery of tourist destinations in Telangana.
-   Support selection and planning across multiple destinations.
-   Estimate travel expenses using machine learning.
-   provide climate-related predictions for travel planning.
-   Estimate expected tourist footfall using historical travel data.
-   Recommend suitable transport modes.
-   Identify potentially deceptive travel reviews using NLP.
-   Detect visible litter in destination images using computer vision.
-   Provide grounded tourism Q&A using Retrieval-Augmented Generation.
-   Combine multiple AI components through an AI trip-planning agent.
-   Store trip requests and generated results for persistence and
    analysis.

------------------------------------------------------------------------

## Key Features

### Destination Discovery

Users can explore tourist destinations across Telangana and select
multiple destinations, including places belonging to different
districts.

Destination information can include:

-   Destination name
-   District
-   Category
-   Rating
-   Popularity
-   Entry fee
-   Latitude and longitude

Selected destinations can be transferred directly to the Trip Planner.

### AI Trip Planner

The Trip Planner acts as the main orchestration layer of the
application.

It combines relevant information from multiple components such as:

-   Destination information
-   Budget prediction
-   Climate prediction
-   Crowd prediction
-   Transport recommendation
-   RAG-based tourism knowledge

The collected context is used by the AI planning layer to generate a
readable trip recommendation.

### Ask Around You

Ask Around You provides an interactive travel-assistance workspace
containing:

-   **Places to Visit** --- RAG-powered tourism Q&A
-   **Budget Advisor** --- available-budget allocation and advisory
-   **Weather** --- climate model predictions
-   **Crowd Insights** --- estimated visitor footfall
-   **Transport** --- route-distance and budget-based transport advisory
-   **Help Me Decide** --- multi-factor destination comparison

### Review Trust Analysis

Users can submit review text for analysis.

The system classifies reviews into:

-   Genuine
-   Deceptive
-   Unverified

Low-confidence predictions are marked as **Unverified** rather than
forcing a binary decision.

### Cleanliness Analyzer

Users can upload destination images for litter detection.

A YOLO-based object detection model identifies visible litter and
provides cleanliness-related analysis.

------------------------------------------------------------------------

## System Architecture

``` text
                         +----------------------+
                         |        USER          |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      FRONTEND        |
                         | HTML / CSS / JS      |
                         +----------+-----------+
                                    |
                             REST API / fetch()
                                    |
                                    v
                         +----------------------+
                         |   FASTAPI BACKEND    |
                         +----------+-----------+
                                    |
        +---------------------------+---------------------------+
        |              |            |            |              |
        v              v            v            v              v
   Destination      ML Models    NLP / CV       RAG        AI Agent
     Service
        |              |            |            |              |
        +---------------------------+---------------------------+
                                    |
                         +----------+-----------+
                         |                      |
                         v                      v
                  Supabase / SQLite          Gemini
```

### Architectural Approach

Around You uses a **multi-model architecture**.

Different tasks have different data structures and objectives.
Therefore:

-   Structured numerical prediction uses classical machine learning.
-   Sequential climate prediction uses deep learning.
-   Review classification uses NLP.
-   Litter detection uses computer vision.
-   Tourism knowledge retrieval uses RAG.
-   Natural-language synthesis and trip orchestration use Generative AI.

FastAPI acts as the central integration layer connecting these
components to the frontend.

------------------------------------------------------------------------

## AI and Machine Learning Components

### 1. Budget Prediction

**Model:** XGBoost Multi-Output Regressor

The budget model predicts multiple travel expense components and an
overall estimated trip cost.

``` text
Trip Details
     |
     v
Preprocessing
     |
     v
XGBoost Multi-Output Regressor
     |
     v
Individual Cost Predictions
     |
     v
Estimated Total Cost
```

XGBoost is suitable for structured/tabular travel data and can model
nonlinear relationships between travel factors and expenses.

------------------------------------------------------------------------

### 2. Climate Prediction

**Model:** Long Short-Term Memory (LSTM)

**Training framework:** PyTorch\
**Deployment format:** ONNX

The climate model provides predictions such as:

-   Maximum temperature
-   Minimum temperature
-   Rainfall probability

``` text
Historical Climate Data
        |
        v
Sequence Preparation
        |
        v
LSTM Network
        |
        v
ONNX Model
        |
        v
Climate Prediction
```

LSTM is used because climate observations are sequential/time-series
data.

------------------------------------------------------------------------

### 3. Crowd Prediction

**Model:** Random Forest Regressor

The crowd module estimates visitor footfall for tourist destinations.

Inputs include structured destination and seasonal information.

The current implementation should be interpreted as **month-level crowd
estimation**, rather than exact day-level visitor prediction.

Season mapping used by the application:

  Months                 Season
  ---------------------- --------------
  December -- February   Winter
  March -- May           Summer
  June -- September      Monsoon
  October -- November    Post-Monsoon

------------------------------------------------------------------------

### 4. Transport Recommendation

**Model:** Random Forest Classifier

The trained transport model recommends transportation modes such as:

-   Car
-   Bus
-   Auto
-   Bike

The model achieved approximately **95.5% accuracy during project
evaluation**.

The Ask Around You transport advisor additionally uses latitude and
longitude to calculate straight-line geographical distance between
selected destinations using the **Haversine formula**.

> Haversine distance represents geographic straight-line distance and
> should not be interpreted as road/driving distance.

------------------------------------------------------------------------

### 5. Review Trust Detection

**Approach:** TF-IDF + Logistic Regression

**Dataset:** Ott Deceptive Opinion Spam Corpus

``` text
Review
  |
  v
Text Preprocessing
  |
  v
TF-IDF Vectorization
  |
  v
Logistic Regression
  |
  v
Confidence Score
  |
  v
Genuine / Deceptive / Unverified
```

The trained model achieved approximately **91.25% accuracy during
project evaluation**.

A confidence threshold is used:

``` text
Confidence >= 70%  -> Genuine / Deceptive
Confidence < 70%   -> Unverified
```

------------------------------------------------------------------------

### 6. Cleanliness Analyzer

**Model:** YOLOv8n

**Dataset:** TACO --- Trash Annotations in Context

Dataset waste categories were consolidated into a general **Litter**
detection class for this application.

``` text
Uploaded Image
      |
      v
YOLOv8n
      |
      v
Litter Detection
      |
      v
Cleanliness Analysis
```

For deployment, the trained model was converted from PyTorch to ONNX:

``` text
PyTorch (.pt) -> ONNX -> ONNX Runtime
```

This provides a lighter production inference environment.

------------------------------------------------------------------------

### 7. Retrieval-Augmented Generation

Around You contains a RAG-based tourism question-answering system.

``` text
User Question
      |
      v
Embedding Generation
      |
      v
Similarity Search
      |
      v
Relevant Telangana Tourism Context
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

The embedding component is based on a **SentenceTransformer model
exported to ONNX**.

RAG retrieves relevant tourism information before the final answer is
generated.

> **RAG retrieves the information; Gemini explains it.**

------------------------------------------------------------------------

### 8. AI Trip Planning Agent

The Trip Planner is not a single prediction model.

It acts as an **orchestration layer** that combines multiple specialized
services.

``` text
Trip Request
      |
      v
Trip Planning Agent
      |
      +---- RAG
      +---- Budget
      +---- Climate
      +---- Crowd
      +---- Transport
      |
      v
Travel Context
      |
      v
Gemini
      |
      v
Personalized Trip Recommendation
```

A deterministic fallback is included so a structured response can still
be produced if the Generative AI call is unavailable.

------------------------------------------------------------------------

## Technology Stack

  Component          Technology
  ------------------ ------------------------------
  Frontend           HTML, CSS, JavaScript
  Backend            Python, FastAPI
  Budget Model       XGBoost
  Climate Model      LSTM / PyTorch
  Crowd Model        Random Forest Regressor
  Transport Model    Random Forest Classifier
  Review NLP         TF-IDF + Logistic Regression
  Computer Vision    YOLOv8n
  Model Deployment   ONNX / ONNX Runtime
  RAG Embeddings     SentenceTransformer
  Generative AI      Gemini
  Cloud Database     Supabase PostgreSQL
  Local Data         SQLite
  Backend Hosting    Render
  Version Control    Git / GitHub

------------------------------------------------------------------------

## Project Structure

``` text
AroundYou/
|
+-- backend/
|   +-- main.py
|   +-- requirements.txt
|   +-- data/
|   |   `-- smart_tourism.db
|   +-- models/
|   +-- routes/
|   +-- services/
|   +-- schemas/
|   `-- agent/
|
+-- frontend/
|   +-- index.html
|   +-- explore.html
|   +-- planner.html
|   +-- ask.html
|   +-- reviews.html
|   +-- cleanliness.html
|   +-- css/
|   |   `-- style.css
|   +-- js/
|   `-- assets/
|
+-- ai/
+-- tools/
+-- .gitignore
`-- README.md
```

------------------------------------------------------------------------

## API Overview

The FastAPI backend exposes REST endpoints used by the frontend.

Important endpoints include:

  Method   Endpoint                        Purpose
  -------- ------------------------------- ------------------------------
  GET      `/api/destinations`             Retrieve destinations
  GET      `/api/destinations/districts`   Retrieve available districts
  POST     `/api/climate/predict`          Climate prediction
  POST     `/api/reviews/classify`         Review trust classification
  POST     `/api/cleanliness/analyze`      Image cleanliness analysis
  POST     `/api/rag/ask`                  Grounded tourism Q&A
  POST     `/api/agent/plan-trip`          AI trip planning

Interactive API documentation is available through FastAPI Swagger when
the backend is running.

------------------------------------------------------------------------

## Database

### Supabase PostgreSQL

Supabase is used for cloud persistence.

Important application tables include:

``` text
trip_requests
trip_results
```

These allow trip inputs and generated outputs to be stored.

### SQLite

Local tourism information and supporting application data are stored in
SQLite where appropriate.

------------------------------------------------------------------------

## Installation and Local Setup

### Prerequisites

Recommended software:

-   Python
-   Git
-   Modern web browser
-   Python virtual environment

### 1. Clone the Repository

``` bash
git clone https://github.com/Akshat5047/AroundYou.git
cd AroundYou
```

### 2. Backend Setup

Navigate to the backend directory:

``` bash
cd backend
```

Create a virtual environment if required:

``` bash
python -m venv venv
```

Activate it on Windows PowerShell:

``` powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Start FastAPI:

``` bash
uvicorn main:app --reload
```

Local API:

``` text
http://127.0.0.1:8000
```

Swagger documentation:

``` text
http://127.0.0.1:8000/docs
```

### 3. Frontend Setup

Open another terminal:

``` bash
cd frontend
python -m http.server 5500
```

Open:

``` text
http://localhost:5500
```

------------------------------------------------------------------------

## Deployment

The FastAPI backend is deployed on **Render**.

Production backend:

``` text
https://aroundyou-api-xi6n.onrender.com
```

API documentation:

``` text
https://aroundyou-api-xi6n.onrender.com/docs
```

The application follows a separated deployment architecture:

``` text
Frontend
    |
    | HTTPS / REST
    v
Render FastAPI Backend
    |
    +-- ML / DL Models
    +-- RAG / AI Agent
    +-- Supabase
    `-- Application Data
```

Final public frontend production deployment is part of the current
implementation stage.

------------------------------------------------------------------------

## Current Status

  Component                     Status
  ----------------------------- -------------
  Destination Discovery         Implemented
  Multi-Destination Selection   Implemented
  Budget Prediction             Integrated
  Climate Prediction            Integrated
  Crowd Prediction              Integrated
  Transport Recommendation      Integrated
  Review Trust Detection        Implemented
  Cleanliness Analyzer          Implemented
  RAG Travel Assistant          Implemented
  Ask Around You                Implemented
  Help Me Decide                Implemented
  AI Trip Planning Agent        Implemented
  Supabase Persistence          Integrated
  FastAPI Backend Deployment    Deployed
  Public Frontend Deployment    In Progress

------------------------------------------------------------------------

## Future Scope

Potential improvements include:

1.  **Public frontend deployment**\
    Complete production hosting and final frontend/backend integration.

2.  **Road-network routing**\
    Replace straight-line Haversine distance with actual road/driving
    routes and travel-time estimates.

3.  **Expanded destination data**\
    Add richer road-access, accommodation, transport, amenity, and
    service information.

4.  **Improved crowd forecasting**\
    Incorporate larger real-world historical datasets, festivals,
    events, holidays, and finer temporal resolution.

5.  **Real-time information**\
    Integrate live weather, transport, traffic, and destination-status
    services where appropriate.

6.  **Model improvement**\
    Continue evaluation, retraining, and optimization as larger datasets
    become available.

7.  **Geographic expansion**\
    Extend the platform beyond Telangana after validating the current
    regional implementation.

------------------------------------------------------------------------

## Academic Note

Around You is developed as an academic project demonstrating the
integration of multiple Data Science and Artificial Intelligence
techniques into a single practical application.

The project demonstrates concepts including:

-   Data preprocessing
-   Regression
-   Classification
-   Time-series deep learning
-   Natural Language Processing
-   Computer Vision
-   Model deployment with ONNX
-   Retrieval-Augmented Generation
-   Generative AI
-   AI agent orchestration
-   REST API development
-   Database integration
-   Cloud deployment

The project intentionally uses specialized models for different tasks
instead of treating Generative AI as a replacement for traditional
Machine Learning and Deep Learning techniques.

------------------------------------------------------------------------

## Project Summary

Around You demonstrates a **multi-model AI architecture for intelligent
travel assistance**.

Rather than relying on a single algorithm, the platform combines:

``` text
Machine Learning
       +
Deep Learning
       +
Natural Language Processing
       +
Computer Vision
       +
Retrieval-Augmented Generation
       +
Generative AI
       |
       v
AI-Powered Travel Advisory Platform
```

The result is a connected system capable of discovering destinations,
generating travel predictions, analyzing reviews and cleanliness,
answering tourism questions, comparing destinations, and producing
AI-assisted trip recommendations.
