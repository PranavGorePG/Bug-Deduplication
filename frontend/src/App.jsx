import React from 'react';
import BugTable from './components/BugTable';

function App() {
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Bug Tracker</h1>
      </header>
      <main className="app-main">
        <BugTable />
      </main>
    </div>
  );
}

export default App;
