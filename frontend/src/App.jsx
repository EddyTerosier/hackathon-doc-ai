import { useEffect, useState } from "react";
import { Navigate, Routes, Route, useLocation } from "react-router-dom";

import MainPage from "./pages/MainPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import EmployeePage from "./pages/EmployeePage";
import AccountantPage from "./pages/AccountantPage";
import { Toaster } from "react-hot-toast";
import { authStorage } from "./auth/authStorage";

import "./App.css";

function AuthenticatedRoute({ children }) {
  const access = authStorage.getAccess();
  const role = authStorage.getRole();

  if (!access || !role) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function RoleProtectedRoute({ allowedRole, children }) {
  const access = authStorage.getAccess();
  const role = authStorage.getRole();

  if (!access || !role) {
    return <Navigate to="/login" replace />;
  }

  if (role !== allowedRole) {
    return <Navigate to="/dashboard/employee" replace />;
  }

  return children;
}

export default function App() {
  const location = useLocation();
  const [displayLocation, setDisplayLocation] = useState(location);
  const showRouteLoader =
    displayLocation.pathname !== location.pathname;

  useEffect(() => {
    if (!showRouteLoader) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setDisplayLocation(location);
    }, 750);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [location, showRouteLoader]);

  return (
    <>
      <Toaster position="top-center" />
      {showRouteLoader ? (
        <div className="route-loader-screen">
          <div className="route-loader-spinner" />
        </div>
      ) : (
        <Routes location={displayLocation}>
          <Route path="/" element={<MainPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard/employee"
            element={
              <AuthenticatedRoute>
                <EmployeePage />
              </AuthenticatedRoute>
            }
          />
          <Route
            path="/dashboard/accountant"
            element={
              <RoleProtectedRoute allowedRole="Accountant">
                <AccountantPage />
              </RoleProtectedRoute>
            }
          />
        </Routes>
      )}
    </>
  );
}
