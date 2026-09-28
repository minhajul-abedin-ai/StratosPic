# StratosPic

### Cloud-Optimized Photo Sharing Web Application

StratosPic is an academic cloud-computing project designed to explore how a modern photo-sharing application can be built with scalability, reliability and containerised deployment in mind.

The project focuses on creating a cloud-native architecture capable of supporting media uploads, image browsing and user interaction while reducing some of the common scalability problems found in traditional web applications.

## Project Overview

Modern media applications need to handle large image files, increasing numbers of users and frequent application updates without causing unnecessary downtime.

StratosPic was designed around these challenges.

The project explores a cloud-based architecture where the application backend can be packaged into containers, deployed to Microsoft Azure and connected to managed infrastructure such as PostgreSQL and virtual networking.

The main areas explored in the project include:

- Reliable media uploading and image viewing
- User interaction and commenting
- Scalable backend services
- Containerised application deployment
- Cloud networking and service isolation
- Centralised container image management
- Cloud-integrated intelligent processing

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python, Flask REST API |
| Database | PostgreSQL |
| Containerisation | Docker |
| Cloud Platform | Microsoft Azure |
| Networking | Azure Virtual Network |
| Deployment | Azure App Service |
| Container Management | Container Registry |

## Cloud Architecture

StratosPic follows a cloud-oriented architecture using Microsoft Azure services.

The original design includes:

**Azure Resource Group**  
Groups the cloud resources used by the application.

**Azure App Service**  
Hosts the StratosPic web application.

**PostgreSQL Database**  
Provides persistent data storage for application information.

**Azure Virtual Network**  
Provides network isolation between cloud resources.

**Container Registry**  
Stores versioned Docker images and supports controlled deployment and rollback.

## Containerisation

The backend was designed around a container-first approach.

Docker provides a consistent environment between development and deployment and reduces environment-specific configuration problems.

Containerisation also makes the architecture easier to scale horizontally as demand increases.

## Problems Addressed

The project was designed around several common challenges in media-heavy web applications:

| Challenge | StratosPic Approach |
|---|---|
| High concurrent traffic | Cloud-hosted, scalable backend architecture |
| Large image files | Optimised media lifecycle design |
| Backend workload | Elastic cloud services |
| Deployment consistency | Docker containers |
| Application updates | Version-controlled container deployment |
| Service isolation | Azure networking architecture |

## Application Features

### Media Lifecycle

Supports the design of efficient uploading and viewing of high-resolution images while aiming to minimise unnecessary latency.

### User Interaction

The architecture supports social interaction around shared media, including commenting functionality.

### Intelligent Operations

The project also explores the use of cloud-integrated AI services to interpret user feedback and extend the platform beyond traditional media hosting.

## Architecture Goals

StratosPic was designed around three main goals:

**Scalability** — allow the application architecture to respond to increasing workloads.

**Reliability** — reduce disruption caused by application updates or infrastructure changes.

**Portability** — use containerisation so application components can behave consistently across environments.

## What I Learned

This project helped me develop a stronger understanding of:

Cloud application architecture, Microsoft Azure services, Python Flask development, Docker containerisation, PostgreSQL integration, virtual networking, scalable system design and cloud deployment concepts.

It also helped me understand why modern applications need to be designed for scalability from the beginning rather than treating scalability as an afterthought.

## Future Development

The architecture could be extended further with automated CI/CD pipelines, object storage for large media files, CDN-based image delivery, monitoring and observability, authentication, automated scaling and more advanced AI-based media analysis.

These are proposed portfolio extensions rather than claims about the original coursework implementation.

## Project Background

StratosPic was originally developed as an academic mini-project during my MSc Computer Science and Technology studies at Ulster University.

This repository presents the project in a cleaner portfolio format while preserving the original cloud-architecture concept.

## Author

**Minhajul Abedin**

MSc Computer Science and Technology  
Ulster University, London

GitHub: [minhajul-abedin-ai](https://github.com/minhajul-abedin-ai)

## Repository

https://github.com/minhajul-abedin-ai/StratosPic
