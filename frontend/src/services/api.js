import axios from 'axios';

// Ensure this points to your FastAPI backend URL
const API_BASE_URL = '/api'; // Adjust port if needed

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getTopics = async () => {
    try {
        const response = await apiClient.get('/topics');
        return response.data; // Should be List[TopicInfo]
    } catch (error) {
        console.error('Error fetching topics:', error);
        throw error; // Re-throw to be handled by the component
    }
};

export const createTopic = async (name = null) => {
    try {
        const payload = name ? { name } : {};
        const response = await apiClient.post('/topics', payload);
        return response.data; // Should be Topic object
    } catch (error) {
        console.error('Error creating topic:', error);
        throw error;
    }
};

export const getTopicHistory = async (topicId) => {
    try {
        const response = await apiClient.get(`/topics/${topicId}`);
        return response.data; // Should be Topic object
    } catch (error) {
        console.error(`Error fetching history for topic ${topicId}:`, error);
        throw error;
    }
};

// 流式响应版本的发送消息函数，使用 fetch API 接收流式数据
export const sendMessage = (topicId, message, onChunkReceived) => {
    // 添加回调参数用于流式更新
    return new Promise((resolve, reject) => {
        // 创建一个对象来存储完整的响应状态
        const responseState = {
            completed: false,
            chunks: [],   // 收到的内容片段
            reply: '',    // 完整回复内容
            topicId: topicId, 
            history: [],  // 完整会话历史
            streaming: true, // 指示是否正在流式接收中
            error: null   // 可能的错误信息
        };
        
        // 创建事件源URL
        const url = `${API_BASE_URL}/topics/${topicId}/messages`;
        
        // 创建POST请求的fetch选项
        const fetchOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message })
        };
        
        // 发送请求并处理流式响应
        fetch(url, fetchOptions)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP错误 ${response.status}`);
                }
                return response.body;
            })
            .then(body => {
                // 获取可读流
                const reader = body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                // 递归读取流数据
                function readStream() {
                    return reader.read().then(({ done, value }) => {
                        if (done) {
                            // 处理可能留在缓冲区的最后数据
                            if (buffer.trim()) {
                                processEventData(buffer);
                            }
                            
                            // 如果流结束但我们没有收到完成事件，手动设置为完成
                            if (!responseState.completed) {
                                responseState.completed = true;
                                responseState.streaming = false;
                                resolve({
                                    reply: responseState.reply,
                                    topic_id: responseState.topicId,
                                    history: responseState.history
                                });
                            }
                            return;
                        }
                        
                        // 解码收到的数据并添加到缓冲区
                        const text = decoder.decode(value, { stream: true });
                        buffer += text;
                        
                        // 处理SSE格式：按行分割，每行以data:开头
                        const lines = buffer.split('\n\n');
                        buffer = lines.pop() || ''; // 保留最后一个可能不完整的行
                        
                        // 处理每一行
                        for (const line of lines) {
                            if (line.trim() && line.startsWith('data:')) {
                                processEventData(line);
                            }
                        }
                        
                        // 继续读取
                        return readStream();
                    });
                }
                
                // 处理SSE事件数据
                function processEventData(line) {
                    try {
                        const data = line.substring(5).trim(); // 移除 'data: '
                        if (!data) return;
                        
                        const event = JSON.parse(data);
                        
                        // 根据事件类型处理
                        switch (event.type) {
                            case 'start':
                                // 开始事件 - 准备接收数据
                                responseState.topicId = event.topicId;
                                break;
                                
                            case 'chunk':
                                // 内容片段 - 添加到响应中
                                responseState.chunks.push(event.content);
                                responseState.reply += event.content;
                                
                                // 使用回调函数而不是resolve，这样可以持续更新UI
                                if (typeof onChunkReceived === 'function') {
                                    onChunkReceived({
                                        reply: responseState.reply,
                                        topic_id: responseState.topicId,
                                        history: responseState.history,
                                        streaming: true // 仍在流式处理中
                                    });
                                }
                                break;
                                
                            case 'error':
                                // 错误事件
                                responseState.error = event.content;
                                responseState.reply = event.content;
                                
                                // 通知错误
                                if (typeof onChunkReceived === 'function') {
                                    onChunkReceived({
                                        reply: responseState.reply,
                                        topic_id: responseState.topicId,
                                        history: responseState.history,
                                        error: responseState.error,
                                        streaming: true
                                    });
                                }
                                break;
                                
                            case 'end':
                                // 完成事件 - 流式响应结束
                                responseState.completed = true;
                                responseState.streaming = false;
                                
                                // 如果收到了历史记录，解析它
                                if (event.history) {
                                    try {
                                        responseState.history = JSON.parse(event.history);
                                    } catch (e) {
                                        console.error('解析历史记录JSON失败:', e);
                                        responseState.history = [];
                                    }
                                }
                                
                                // 解析消息完成，返回结果
                                resolve({
                                    reply: responseState.reply,
                                    topic_id: responseState.topicId,
                                    history: responseState.history,
                                    streaming: false // 已完成
                                });
                                break;
                                
                            default:
                                console.warn('未知的事件类型:', event.type);
                        }
                    } catch (e) {
                        console.error('处理事件数据失败:', e, line);
                    }
                }
                
                // 开始读取流
                return readStream();
            })
            .catch(error => {
                console.error(`向主题 ${topicId} 发送消息时出错:`, error);
                reject(new Error(error.message || '发送消息失败'));
            });
    });
};

// Optional: Function to trigger ingestion (if you want a button for it)
export const triggerIngestion = async () => {
    try {
        const response = await apiClient.post('/ingest');
        return response.data; // { message: "..." }
    } catch (error) {
        console.error('Error triggering ingestion:', error);
         const errorData = error.response?.data || { detail: 'Network error or backend unreachable' };
        throw new Error(errorData.detail || 'Failed to trigger ingestion');
    }
}

export const deleteTopic = async (topicId) => {
    try {
        const response = await apiClient.delete(`/topics/${topicId}`);
        return response.data; // Should be { message: "..." }
    } catch (error) {
        console.error(`Error deleting topic ${topicId}:`, error);
        const errorData = error.response?.data || { detail: 'Network error or backend unreachable' };
        throw new Error(errorData.detail || 'Failed to delete topic');
    }
};