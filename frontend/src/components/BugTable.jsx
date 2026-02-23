import React, { useState, useEffect } from 'react';
// import { bugs } from '../data/bugs'; // Removed static import
import DuplicateModal from './DuplicateModal';

const BugTable = () => {
  const [bugs, setBugs] = useState([]);
  const [duplicateResults, setDuplicateResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [selectedBugIndex, setSelectedBugIndex] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const fetchBugs = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/external-bugs');
        if (!response.ok) {
            throw new Error('Failed to fetch bugs');
        }
        const data = await response.json();
        setBugs(data);
      } catch (error) {
        console.error('Error fetching bugs:', error);
        alert('Failed to load bugs from external API.');
      } finally {
        setFetching(false);
      }
    };

    fetchBugs();
  }, []);

  const handleCheckDuplicates = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/process-json', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(bugs.map((bug) => ({
          id: bug.id, // Use actual UUID from API
          title: bug.title,
          repro_steps: bug.repro_steps || bug.description || '' // Fallback to description if repro_steps is null
        }))),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      // Map results to index for easy lookup (since we iterate by index in render)
      const resultsMap = {};
      data.forEach((result, index) => {
        resultsMap[index] = result;
      });
      setDuplicateResults(resultsMap);
    } catch (error) {
      console.error('Error checking duplicates:', error);
      alert('Failed to check duplicates. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDuplicate = (index) => {
    setSelectedBugIndex(index);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedBugIndex(null);
  };

  if (fetching) {
      return <div className="bug-table-container">Loading bugs...</div>;
  }

  return (
    <div className="bug-table-container">
      <div className="table-header">
        <div className="header-left">
          <h2>Bug Reports</h2>
          <span className="badge">{bugs.length} Issues</span>
        </div>
        <button 
          className="check-duplicates-btn" 
          onClick={handleCheckDuplicates} 
          disabled={loading}
        >
          {loading ? 'Checking...' : 'Check Duplicates'}
        </button>
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th className="col-id">ID</th>
              <th className="col-title">Title</th>
              <th className="col-repro">Reproduction Steps / Issue</th>
              <th className="col-status-type">Bug Status</th>
              <th className="col-status">Duplicate Status</th>
            </tr>
          </thead>
          <tbody>
            {bugs.map((bug, index) => {
              const result = duplicateResults[index];
              return (
                <tr key={bug.id || index}>
                  <td className="col-id" title={bug.id}>
                      {/* Truncate UUID for display, allow hover for full */}
                      {bug.id ? `${bug.id.substring(0, 8)}...` : `#${index + 1}`}
                  </td>
                  <td className="col-title">
                      <div className="bug-title">{bug.title}</div>
                  </td>
                  <td className="col-repro">
                    {/* Show repro_steps or fallback description */}
                    <div className="repro-steps">{bug.repro_steps || bug.description}</div>
                  </td>
                  <td className="col-status-type">
                    {result ? (
                       (() => {
                           // Logic based on result string as requested
                           const resString = result.result || '';
                           let statusText = 'New Bug';
                           let statusClass = 'status-new';

                           if (resString.includes('Appended above')) {
                               statusText = 'Already Appended';
                               statusClass = 'status-appended';
                           } else if (resString.includes('Exact found')) {
                               // Exact match in DB
                               statusText = 'Bug Already Raised';
                               statusClass = 'status-raised';
                           } else if (result.matches && result.matches.length > 0) {
                               // Matches found (Confirmed or Candidates)
                               statusText = 'Similar Bug Present';
                               statusClass = 'status-similar';
                           } else {
                               // Truly Unique (No matches returned)
                               statusText = 'New Bug';
                               statusClass = 'status-new';
                           }
                           
                           // Self-reference check override not needed as much with UUIDs if backend handles it correctly
                           if (result.duplicate_of_row_index === index) {
                                statusText = 'New Bug';
                                statusClass = 'status-new';
                           }

                           return (
                               <span className={`status-badge ${statusClass}`}>
                                   {statusText}
                               </span>
                           );
                       })()
                    ) : (
                        <span className="status-pending">-</span>
                    )}
                  </td>
                  <td className="col-status">
                    {result ? (
                      (() => {
                         const isSelfReference = result.duplicate_of_row_index === index;
                         const isUnique = result.result.includes('Not Found') || isSelfReference;
                         
                         return (
                          <button 
                            className={`view-duplicate-btn ${isUnique ? 'btn-unique' : 'btn-duplicate'}`}
                            onClick={() => handleViewDuplicate(index)}
                          >
                            {isUnique ? 'Check Duplicate' : 'View Duplicate'}
                          </button>
                         );
                      })()
                    ) : (
                      <span className="status-pending">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {isModalOpen && selectedBugIndex !== null && duplicateResults[selectedBugIndex] && (
        <DuplicateModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          originalBug={bugs[selectedBugIndex]}
          originalIndex={selectedBugIndex}
          result={duplicateResults[selectedBugIndex]}
          allBugs={bugs}
        />
      )}
    </div>
  );
};

export default BugTable;
