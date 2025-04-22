import React, { useState, useRef, useEffect } from 'react';
import Message from './Message';
import * as api from '../services/api';
import './ChatWindow.css'; // Create this CSS file

function ChatWindow({ selectedTopicId, topicData, onMessagesUpdate }) {
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [streamingReply, setStreamingReply] = useState(''); // 存储流式接收到的回复
    const [isStreaming, setIsStreaming] = useState(false); // 指示是否正在流式接收中
    const messagesEndRef = useRef(null); // To scroll to bottom

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Scroll to bottom when messages change or topic changes
    useEffect(() => {
        scrollToBottom();
    }, [topicData?.messages, selectedTopicId]); // Trigger on messages or topic change


    const handleSendMessage = async (e) => {
        e.preventDefault(); // Prevent form submission page reload
        if (!inputMessage.trim() || !selectedTopicId || isLoading) return;

        const messageToSend = inputMessage;
        setInputMessage(''); // Clear input immediately
        setIsLoading(true);
        setError(null);
        setIsStreaming(true); // 开始流式接收
        setStreamingReply(''); // 清空之前的流式内容
        
        // 立即添加用户消息，提高用户体验
        const optimisticUserMessage = { role: 'user', content: messageToSend };
        const currentMessages = [...(topicData?.messages || []), optimisticUserMessage];
        onMessagesUpdate(selectedTopicId, currentMessages);
        
        // 添加空的AI消息占位，准备流式显示
        const placeholderAiMessage = { role: 'assistant', content: '' };
        const messagesWithPlaceholder = [...currentMessages, placeholderAiMessage];
        onMessagesUpdate(selectedTopicId, messagesWithPlaceholder);

        try {
            // 定义流式更新的回调函数
            const handleStreamUpdate = (response) => {
                if (response.streaming) {
                    // 流式更新 - 更新临时显示
                    setStreamingReply(response.reply);
                    
                    // 更新消息列表中的最后一条消息(AI回复)
                    const updatedMessages = [...currentMessages];
                    // 始终存在一个 AI 消息，因为我们已经添加了占位消息
                    if (updatedMessages.length > 0) {
                        // 找到最后一个占位消息并更新它
                        const lastMessageIndex = messagesWithPlaceholder.length - 1;
                        messagesWithPlaceholder[lastMessageIndex].content = response.reply;
                        onMessagesUpdate(selectedTopicId, messagesWithPlaceholder);
                    }
                }
            };

            // 使用新的回调方式调用流式 API
            const finalResponse = await api.sendMessage(
                selectedTopicId, 
                messageToSend,
                handleStreamUpdate // 传递回调函数处理各个块
            );
            
            // 流式数据全部接收完毕
            setIsStreaming(false);
            
            // 使用后端返回的完整历史
            if (finalResponse.history && finalResponse.history.length > 0) {
                onMessagesUpdate(selectedTopicId, finalResponse.history);
            }
            
        } catch (err) {
            console.error("发送消息错误:", err);
            setError(err.message || '发送消息失败，请重试。');
            const errorMessage = { role: 'assistant', content: `错误: ${err.message}` };
            onMessagesUpdate(selectedTopicId, [...currentMessages, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    if (!selectedTopicId) {
        return <div className="chat-window-placeholder">Select or create a topic to start chatting.</div>;
    }

    if (!topicData) {
         return <div className="chat-window-placeholder">Loading topic data...</div>; // Or handle loading state
    }


    return (
        <div className="chat-window-container">
            <div className="chat-messages">
                {topicData?.messages?.map((message, index) => (
                    <Message 
                        key={`msg-${index}`} 
                        message={message} 
                        isLastMessage={index === topicData.messages.length - 1 && message.role === 'assistant'}
                        isStreaming={isStreaming && index === topicData.messages.length - 1 && message.role === 'assistant'}
                    />
                ))}
                <div ref={messagesEndRef} /> {/* 滚动到的元素 */}
                {/* Display error message */}
                {error && (
                    <div className="message assistant-message">
                        <div className="message-bubble error-bubble">
                            <p>Error: {error}</p>
                        </div>
                    </div>
                )}
            </div>
            <form className="chat-input-form" onSubmit={handleSendMessage}>
                <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Ask your study assistant..."
                    disabled={isLoading || !selectedTopicId}
                />
                <button type="submit" disabled={isLoading || !inputMessage.trim()}>
                    Send
                </button>
            </form>
        </div>
    );
}

export default ChatWindow;