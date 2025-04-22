// frontend/src/components/TopicList.jsx

import React from 'react';
import './TopicList.css';
// Optional: Import delete icon
import { FaTrashAlt } from 'react-icons/fa';

// Receive onDeleteTopic prop from App.jsx
function TopicList({ topics, selectedTopicId, onSelectTopic, onCreateTopic, onDeleteTopic, isLoading }) {

    // Prevent click on delete button from selecting the topic
    const handleDeleteClick = (e, topicId) => {
        e.stopPropagation(); // Stop the click from bubbling up to the li
        onDeleteTopic(topicId); // Call the handler passed from App
    };

    return (
        <div className="topic-list-container">
            <h3>Topics</h3>
            <button
                className="new-topic-button"
                onClick={onCreateTopic}
                disabled={isLoading}
            >
                New Topic
            </button>
            {isLoading && topics.length === 0 && <p>Loading topics...</p>} {/* Show loading only if list is empty */}
            {!isLoading && topics.length === 0 && <p>No topics yet. Create one!</p>}
            <ul className="topic-list">
                {topics.map((topic) => (
                    <li
                        key={topic.id}
                        className={`topic-item ${topic.id === selectedTopicId ? 'selected' : ''}`}
                        onClick={() => onSelectTopic(topic.id)} // Select on li click
                    >
                        <div className="topic-info"> {/* Wrap text content */}
                           <span className="topic-name">{topic.name}</span>
                           <span className="topic-preview">{topic.preview}</span>
                        </div>
                        {/* Add Delete Button */}
                        <button
                            className="delete-topic-button"
                            onClick={(e) => handleDeleteClick(e, topic.id)}
                            disabled={isLoading} // Disable button while any list loading/deleting
                            title={`Delete topic: ${topic.name}`} // Tooltip for accessibility
                        >
                             <FaTrashAlt /> {/* Use Trash icon */}
                             {/* Or use simple text: X */}
                        </button>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default TopicList;