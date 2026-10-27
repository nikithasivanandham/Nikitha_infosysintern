# ✈️ Airport Operations Coordination Engine

### Infosys Internship 7.0 | Milestone 1 | Frontend Development

## 📌 Project Overview

The Airport Operations Coordination Engine is a frontend application designed to provide a common interface for monitoring airport operations, including flight operations, weather alerts, gate and resource availability, staff allocation, and AI-assisted decision support.

This contribution focuses on developing the common frontend application shell, mock login flow, dashboard layout, and navigation between operational modules.

## 🎯 Objective

To build a consistent and user-friendly frontend foundation for the Airport Operations Coordination Engine as part of Milestone 1 of Infosys Internship 7.0.

## 📸 Proof of Work

## Login page
![image alt](https://github.com/madhuradarshinirm/Airport-Operations-Coordination-Decision-Engine/blob/8159180385957f46b01cefc30d48485c22b30817/Screenshot%202026-10-22%20141121.png)

## Dashboard overview page
![image alt](https://github.com/madhuradarshinirm/Airport-Operations-Coordination-Decision-Engine/blob/57e804ae1fb507b8d2df5296f15345818540da21/Screenshot%202026-10-22%20141145.png)

## ✨ Features Implemented

- 🔐 **Mock Login:** Login page demonstrating the sign-in flow without backend authentication.
- 📊 **Operations Dashboard:** Common overview page for airport operations.
- 🧭 **Sidebar Navigation:** Navigation across six application sections.
- ✈️ **Flight Operations:** Dedicated page for flight-related information.
- 🌦️ **Weather & Alerts:** Dedicated page for weather and operational alerts.
- 🚪 **Gates & Resources:** Dedicated page for gate and resource information.
- 👥 **Staff Allocation:** Dedicated page for staff allocation information.
- 🧠 **AI Decisions:** Dedicated page for AI agent and decision-support information.
- 🚪 **Mock Sign-Out:** Clears the demo login state and returns to the login page.
- 🎨 **Consistent UI:** Dark navy theme, cyan accents, reusable layout components, and consistent styling.

## 🛠️ Technologies Used

- React.js
- JavaScript
- Vite
- Tailwind CSS
- React Router DOM
- Lucide React
- HTML5
- Git and GitHub
- Visual Studio Code

## 🚀 Installation and Setup

### Prerequisites

- Node.js
- npm
- Git
- Visual Studio Code

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### Step 2: Navigate to the Project Folder

```bash
cd airport-operations-frontend
```

### Step 3: Install Dependencies

```bash
npm install
```

### Step 4: Start the Development Server

```bash
npm run dev
```

Open the local URL displayed in the terminal, usually `http://localhost:5173/`.

### Step 5: Build the Project

```bash
npm run build
```

## 📂 Project Structure

```text
airport-operations-frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Header.jsx
│   │   └── Sidebar.jsx
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Flights.jsx
│   │   ├── Weather.jsx
│   │   ├── Resources.jsx
│   │   ├── Staff.jsx
│   │   └── AIDecisions.jsx
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
├── .gitignore
└── README.md
```

## ✅ Milestone 1 Frontend Progress

- Created the React + Vite frontend project.
- Developed the common application shell and dashboard layout.
- Implemented the mock login page.
- Connected the login flow to the dashboard.
- Implemented navigation across six operational sections.
- Implemented the mock sign-out flow.
- Tested login, navigation, and sign-out in the browser.

## ⚠️ Prototype Limitations

This frontend is a demonstration prototype. Some module content and operational data are placeholders pending backend, API, and team-module integration. The mock login accepts any non-empty email and password and is not production-grade authentication.

The application is intended to support operational visibility and future decision-support workflows. Any operational recommendations must remain advisory and subject to authorized human review and approval.

## 🔮 Future Enhancements

- Integrate backend authentication and API endpoints.
- Connect live flight and weather data.
- Integrate gate, resource, and staff information.
- Connect AI agent workflows and decision-support features.
- Implement approval and rejection workflows.
- Improve loading, error, and empty states.
- Add automated testing and responsive-layout improvements.


Developed as part of Infosys Internship 7.0.
