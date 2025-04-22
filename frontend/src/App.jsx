// frontend/src/App.jsx

import React, { useState, useEffect, useCallback } from 'react';
import TopicList from './components/TopicList';
import ChatWindow from './components/ChatWindow';
import * as api from './services/api';
import './App.css';

function App() {
    const [topics, setTopics] = useState([]);
    const [selectedTopicId, setSelectedTopicId] = useState(null);
    const [currentTopicData, setCurrentTopicData] = useState(null);
    const [isTopicsLoading, setIsTopicsLoading] = useState(true);
    const [isChatLoading, setIsChatLoading] = useState(false);
    const [error, setError] = useState(null);
    // Add a loading state specific for delete operations
    const [isDeleting, setIsDeleting] = useState(false);


    const fetchTopics = useCallback(async () => {
        // ... (fetchTopics function remains the same) ...
        setIsTopicsLoading(true);
        setError(null);
        try {
            const topicsList = await api.getTopics();
            setTopics(topicsList);
        } catch (err) {
            console.error("Error fetching topics:", err);
            setError("Failed to load topics. Ensure the backend is running.");
        } finally {
            setIsTopicsLoading(false);
        }
    }, []);


    useEffect(() => {
        fetchTopics();
    }, [fetchTopics]);

    useEffect(() => {
        // ... (useEffect for fetching topic data remains the same) ...
        if (!selectedTopicId) {
            setCurrentTopicData(null);
            return;
        }
        const fetchTopicData = async () => {
            // ... (logic for fetching history) ...
             setIsChatLoading(true);
            setError(null);
            try {
                const topicData = await api.getTopicHistory(selectedTopicId);
                setCurrentTopicData(topicData);
            } catch (err) {
                console.error(`Error fetching topic ${selectedTopicId}:`, err);
                setError(`Failed to load chat history for topic ${selectedTopicId}.`);
                setCurrentTopicData(null);
            } finally {
                setIsChatLoading(false);
            }
        };
        fetchTopicData();
    }, [selectedTopicId]);


    const handleSelectTopic = (topicId) => {
        // ... (handleSelectTopic function remains the same) ...
        if (topicId !== selectedTopicId) {
            setSelectedTopicId(topicId);
        }
    };

    const handleCreateTopic = async () => {
        // ... (handleCreateTopic function remains the same) ...
        setIsTopicsLoading(true);
         setError(null);
        try {
            const newTopic = await api.createTopic();
            // Use TopicInfo structure for consistency in the list
            const newTopicInfo = { id: newTopic.id, name: newTopic.name, preview: "New Topic" };
            setTopics(prevTopics => [...prevTopics, newTopicInfo]);
            setCurrentTopicData(newTopic);
            setSelectedTopicId(newTopic.id);
        } catch (err) {
             console.error("Error creating topic:", err);
             setError("Failed to create new topic.");
        } finally {
             setIsTopicsLoading(false);
        }
    };

    const handleMessagesUpdate = useCallback((topicId, updatedMessages) => {
       // ... (handleMessagesUpdate function remains the same) ...
        setCurrentTopicData(prevData => {
            if (prevData && prevData.id === topicId) {
                return { ...prevData, messages: updatedMessages };
            }
            return prevData;
        });
        setTopics(prevTopics => prevTopics.map(t => {
            if (t.id === topicId) {
                const firstUserMsg = updatedMessages.find(m => m.role === 'user');
                const newPreview = firstUserMsg
                   ? firstUserMsg.content.substring(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '')
                   : (t.preview === "New Topic" && updatedMessages.length > 0 ? updatedMessages[0].content.substring(0, 50) + '...' : t.preview); // Update preview slightly better
                return { ...t, preview: newPreview };
            }
            return t;
        }));
    }, []);

    // --- NEW: Handler for deleting a topic ---
    const handleDeleteTopic = useCallback(async (topicIdToDelete) => {
        // Prevent deletion if another delete is in progress
        if (isDeleting) return;

        // Confirmation dialog
        if (!window.confirm(`Are you sure you want to delete this topic? This action cannot be undone.`)) {
            return;
        }

        setIsDeleting(true);
        setError(null);

        try {
            await api.deleteTopic(topicIdToDelete);

            // Update topics list state
            setTopics(prevTopics => prevTopics.filter(topic => topic.id !== topicIdToDelete));

            // If the deleted topic was the selected one, clear selection and chat
            if (selectedTopicId === topicIdToDelete) {
                setSelectedTopicId(null);
                setCurrentTopicData(null);
            }

        } catch (err) {
            console.error(`Error deleting topic ${topicIdToDelete}:`, err);
            setError(`Failed to delete topic: ${err.message}`);
            // Optionally add the topic back to the list visually if deletion failed?
            // Or just show the error banner.
        } finally {
            setIsDeleting(false);
        }
    }, [selectedTopicId, isDeleting]); // Add dependencies

    return (
        <div className="app-container">
            <aside className="sidebar">
                <TopicList
                    topics={topics}
                    selectedTopicId={selectedTopicId}
                    onSelectTopic={handleSelectTopic}
                    onCreateTopic={handleCreateTopic}
                    onDeleteTopic={handleDeleteTopic} // <-- Pass down delete handler
                    isLoading={isTopicsLoading || isDeleting} // <-- Combine loading states
                />
            </aside>
            <main className="chat-area">
                 {error && <div className="error-banner">{error}</div>}
                <ChatWindow
                    selectedTopicId={selectedTopicId}
                    topicData={isChatLoading ? null : currentTopicData}
                    onMessagesUpdate={handleMessagesUpdate}
                />
            </main>
        </div>
    );
}

export default App;