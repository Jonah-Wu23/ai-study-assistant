import React, { useState, useEffect, useRef } from 'react';
import './Message.css'; // 样式文件

function Message({ message, isLastMessage = false, isStreaming = false }) {
    const { role, content } = message;
    const isUser = role === 'user';
    const [displayContent, setDisplayContent] = useState(content);
    const prevContentRef = useRef("");
    
    // 当内容变化时更新显示内容
    useEffect(() => {
        // 如果是普通消息或不是正在流式处理的消息，直接显示完整内容
        if (isUser || !isStreaming || !isLastMessage) {
            setDisplayContent(content);
            prevContentRef.current = content;
        } else if (isLastMessage && isStreaming && content !== prevContentRef.current) {
            // 只有当是最后一条消息、正在流式处理、内容有变化时才更新
            setDisplayContent(content);
            prevContentRef.current = content;
        }
    }, [content, isUser, isStreaming, isLastMessage]);
    
    // 如果是AI消息且内容为空，则不显示该消息
    if (!isUser && !content && !isStreaming) {
        return null;
    }

    return (
        <div className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
            <div className={`message-bubble ${isStreaming && isLastMessage ? 'streaming' : ''}`}>
                {/* 当是AI回复且内容为空时，仅显示打字指示器 */}
                {!isUser && displayContent === '' && isStreaming ? (
                    <div className="typing-indicator-inline">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                ) : (
                    <>
                        <p>{displayContent}</p>
                        {isStreaming && isLastMessage && displayContent && (
                            <span className="cursor"></span>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

export default Message;