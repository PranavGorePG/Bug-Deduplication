import React from 'react';

const DuplicateModal = ({ isOpen, onClose, originalBug, result, allBugs, originalIndex }) => {
    if (!isOpen || !result) return null;

    // Determine if it's a unique bug (no duplicates found)
    // Logic from previous step: if duplicate_of_row_index is self, it's unique.
    const isSelfReference = result.duplicate_of_row_index === originalIndex;
    const displayText = isSelfReference ? 'Unique' : result.result;
    const isUnique = displayText.includes('Not Found') || displayText === 'Unique';

    // Find the bug it is a duplicate of (if applicable)
    let parentBug = null;
    if (!isUnique && result.duplicate_of_row_index !== undefined && result.duplicate_of_row_index !== null) {
        parentBug = allBugs[result.duplicate_of_row_index];
    }

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <div className="modal-header">
                    <h3>Duplicate Analysis</h3>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body">
                    {/* Left Side: Original Bug */}
                    <div className="bug-column original-column">
                        <h4>Original Request</h4>
                        <div className="bug-details">
                            <div className="detail-group">
                                <label>ID:</label>
                                <span>{originalBug.id ? originalBug.id : `#${originalIndex + 1}`}</span>
                            </div>
                            <div className="detail-group">
                                <label>Title:</label>
                                <p>{originalBug.title}</p>
                            </div>
                            <div className="detail-group">
                                <label>Repro Steps:</label>
                                <pre>{originalBug.repro_steps || originalBug.description}</pre>
                            </div>
                        </div>
                    </div>

                    {/* Right Side: Analysis Results */}
                    <div className="bug-column analysis-column">
                        <h4>Analysis Result: <span className={`status-badge ${isUnique ? 'status-unique' : 'status-duplicate'}`}>{displayText}</span></h4>

                        <div className="bug-details">
                            {/* If it's a duplicate of another row, show that row's details */}
                            {parentBug && (
                                <div className="duplicate-source">
                                    <h5>Duplicate of (Row #{result.duplicate_of_row_index + 1}):</h5>
                                    <div className="detail-group">
                                        <label>Title:</label>
                                        <p>{parentBug.title}</p>
                                    </div>
                                    <div className="detail-group">
                                        <label>Repro Steps:</label>
                                        <pre>{parentBug.repro_steps || parentBug.description}</pre>
                                    </div>
                                </div>
                            )}

                            {/* Show similar matches from vector store */}
                            {result.matches && result.matches.length > 0 && (
                                <div className="matches-list">
                                    <h5>Similar Existing Bugs:</h5>
                                    {result.matches.map((match, i) => (
                                        
                                        <div key={i} className="match-item">
                                            <div className="match-header">
                                                <span className="match-id">ID: {match.id}</span>
                                                <span className="match-score">({match.score_pct.toFixed(1)}% Match)</span>
                                            </div>
                                            <p className="match-title">{match.title}</p>
                                            <p className="match-repro">Repro Steps: {match.repro_steps}</p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {isUnique && !result.matches?.length && (
                                <p className="no-matches">No similar bugs found.</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DuplicateModal;
