import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations } from '../locales/translation';
import { authService } from '../services/authService';

// Create individual Contexts
const LanguageContext = createContext();
const ThemeContext = createContext();
const AccessibilityContext = createContext();
const AuthContext = createContext();
const AppDataContext = createContext();

// Custom Hooks for easy usage
export const useLanguage = () => useContext(LanguageContext);
export const useTheme = () => useContext(ThemeContext);
export const useAccessibility = () => useContext(AccessibilityContext);
export const useAuth = () => useContext(AuthContext);
export const useAppData = () => useContext(AppDataContext);

export const AppProvider = ({ children }) => {
  // --- LOCALIZATION STATE ---
  const [language, setLanguageState] = useState(() => {
    return localStorage.getItem('language') || 'en';
  });

  const setLanguage = (lang) => {
    setLanguageState(lang);
    localStorage.setItem('language', lang);
  };

  const t = (key) => {
    const localeTranslations = translations[language] || translations['en'];
    return localeTranslations[key] || translations['en'][key] || key;
  };

  // --- THEME STATE ---
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });

  const setTheme = (newTheme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  // Listen to system theme changes if theme is set to 'system'
  useEffect(() => {
    if (theme !== 'system') return;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      const root = window.document.documentElement;
      root.classList.remove('light', 'dark');
      root.classList.add(mediaQuery.matches ? 'dark' : 'light');
    };
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // --- ACCESSIBILITY STATE ---
  const [largerText, setLargerTextState] = useState(() => {
    return localStorage.getItem('accessibility-larger-text') === 'true';
  });
  const [highContrast, setHighContrastState] = useState(() => {
    return localStorage.getItem('accessibility-high-contrast') === 'true';
  });

  const setLargerText = (val) => {
    setLargerTextState(val);
    localStorage.setItem('accessibility-larger-text', val);
  };

  const setHighContrast = (val) => {
    setHighContrastState(val);
    localStorage.setItem('accessibility-high-contrast', val);
  };

  useEffect(() => {
    const body = window.document.body;
    if (largerText) {
      body.classList.add('accessibility-large-text');
    } else {
      body.classList.remove('accessibility-large-text');
    }
  }, [largerText]);

  useEffect(() => {
    const body = window.document.body;
    if (highContrast) {
      body.classList.add('accessibility-high-contrast');
    } else {
      body.classList.remove('accessibility-high-contrast');
    }
  }, [highContrast]);

  // --- AUTH STATE ---
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('user');
      if (savedUser) return JSON.parse(savedUser);
      // Guest mode: rebuild the guest profile so a page refresh doesn't log the user out
      if (localStorage.getItem('isGuest') === 'true') {
        return {
          name: "Guest User",
          email: "guest@sahakarsahayak.gov.in",
          phone: "0000000000",
          userType: "Citizen",
          preferredLanguage: localStorage.getItem('language') || 'en'
        };
      }
    } catch (e) {
      // ignore broken saved data
    }
    return null;
  });
  const [token, setToken] = useState(() => {
    return localStorage.getItem('token') || null;
  });
  const [isGuest, setIsGuest] = useState(() => {
    return localStorage.getItem('isGuest') === 'true';
  });

  // Verify and sync session on initial load if token exists
  useEffect(() => {
    if (token && !isGuest) {
      authService.getMe(token).then((userData) => {
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      }).catch((err) => {
        console.warn('Session check:', err.message);
      });
    }
  }, [token, isGuest]);

  const login = async (identifier, password) => {
    const res = await authService.login(identifier, password);
    setUser(res.user);
    setToken(res.token);
    setIsGuest(false);
    localStorage.setItem('user', JSON.stringify(res.user));
    localStorage.setItem('token', res.token);
    localStorage.setItem('isGuest', 'false');
    if (res.user?.preferredLanguage && res.user.preferredLanguage !== language) {
      setLanguage(res.user.preferredLanguage);
    }
    return res;
  };

  const register = async (nameOrObj, email, phone, password, userType, preferredLanguage) => {
    let payload;
    if (typeof nameOrObj === 'object' && nameOrObj !== null) {
      payload = {
        name: nameOrObj.name,
        email: nameOrObj.email,
        phone: nameOrObj.phone,
        password: nameOrObj.password,
        userType: nameOrObj.userType || 'Citizen',
        preferredLanguage: nameOrObj.preferredLanguage || language,
      };
    } else {
      payload = {
        name: nameOrObj,
        email,
        phone,
        password,
        userType: userType || 'Citizen',
        preferredLanguage: preferredLanguage || language,
      };
    }

    const res = await authService.register(payload);
    setUser(res.user);
    setToken(res.token);
    setIsGuest(false);
    localStorage.setItem('user', JSON.stringify(res.user));
    localStorage.setItem('token', res.token);
    localStorage.setItem('isGuest', 'false');
    if (res.user?.preferredLanguage && res.user.preferredLanguage !== language) {
      setLanguage(res.user.preferredLanguage);
    }
    return res;
  };

  const completeAuthSession = (authData) => {
    if (!authData || !authData.user || !authData.token) return;
    setUser(authData.user);
    setToken(authData.token);
    setIsGuest(false);
    localStorage.setItem('user', JSON.stringify(authData.user));
    localStorage.setItem('token', authData.token);
    localStorage.setItem('isGuest', 'false');
    if (authData.user?.preferredLanguage && authData.user.preferredLanguage !== language) {
      setLanguage(authData.user.preferredLanguage);
    }
  };

  const continueAsGuest = () => {
    const guestUser = {
      name: "Guest User",
      email: "guest@sahakarsahayak.gov.in",
      phone: "0000000000",
      userType: "Citizen",
      preferredLanguage: language
    };
    setUser(guestUser);
    setToken(null);
    setIsGuest(true);
    localStorage.setItem('isGuest', 'true');
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setIsGuest(false);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.setItem('isGuest', 'false');
  };

  const updateProfile = async (name, email, phone, prefLang, uType) => {
    if (isGuest) {
      const updatedUser = { ...user, name, email, phone, preferredLanguage: prefLang, userType: uType };
      setUser(updatedUser);
      if (prefLang !== language) setLanguage(prefLang);
      return updatedUser;
    }

    if (token) {
      const res = await authService.updateProfile(
        { name, email, phone, preferredLanguage: prefLang, userType: uType },
        token
      );
      setUser(res.user);
      if (res.token) {
        setToken(res.token);
        localStorage.setItem('token', res.token);
      }
      localStorage.setItem('user', JSON.stringify(res.user));
      if (prefLang !== language) setLanguage(prefLang);
      return res.user;
    } else {
      const updatedUser = { ...user, name, email, phone, preferredLanguage: prefLang, userType: uType };
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      if (prefLang !== language) setLanguage(prefLang);
      return updatedUser;
    }
  };

  // --- APP MOCK DATA STORE ---
  // Store chat history and saved answers dynamically in state, prefilled with rich mock data
  const [chatHistory, setChatHistory] = useState(() => {
    const savedHistory = localStorage.getItem('chatHistory');
    if (savedHistory) return JSON.parse(savedHistory);

    // Initial mock chat history
    const initialHistory = [
      {
        id: "chat-1",
        title: "Cooperative Registration Documents",
        lastMessage: "You will need bylaws, citizen copies, and at least 25 members.",
        date: "2026-08-30T10:30:00Z",
        language: "en",
        category: "Registration",
        messages: [
          { sender: "user", text: "How do I register a cooperative?", time: "2026-08-30T10:28:00Z" },
          { 
            sender: "assistant", 
            text: "To register a cooperative, you typically need to gather a minimum number of members (often 25), write proposed bylaws, and submit an application to the regulatory body. Key documents include citizen cards, a viability report, and minutes of the initial assembly.",
            time: "2026-08-30T10:30:00Z",
            sources: [
              { documentName: "Cooperative Act, Sec 4", provision: "Registration Requirements", id: "source-1" }
            ]
          }
        ]
      },
      {
        id: "chat-2",
        title: "Member Rights and Voting",
        lastMessage: "Yes, every member has one vote regardless of share capital.",
        date: "2026-08-25T14:15:00Z",
        language: "en",
        category: "Membership",
        messages: [
          { sender: "user", text: "Does a member with more shares get more votes?", time: "2026-08-25T14:12:00Z" },
          {
            sender: "assistant",
            text: "No, one of the core principles of cooperatives is democratic member control. This means each member has exactly one vote, regardless of the number of shares they own. This ensures equality in governance.",
            time: "2026-08-25T14:15:00Z",
            sources: [
              { documentName: "Cooperative Principles Handbook", provision: "Principle 2: Democratic Control", id: "source-2" }
            ]
          }
        ]
      },
      {
        id: "chat-3",
        title: "समिति गठन प्रक्रिया",
        lastMessage: "सहकारी सञ्चालक समिति निर्वाचन साधारण सभाबाट हुन्छ ।",
        date: "2026-08-20T09:10:00Z",
        language: "ne",
        category: "Governance",
        messages: [
          { sender: "user", text: "सहकारी समिति कसरी गठन हुन्छ?", time: "2026-08-20T09:05:00Z" },
          {
            sender: "assistant",
            text: "सहकारीको सञ्चालक समिति साधारण सभाद्वारा निर्वाचित हुन्छ। समितिमा साधारणतया अध्यक्ष र अन्य सदस्यहरू गरी ५ देखि ११ जनासम्म सदस्य रहने व्यवस्था सहकारी ऐन तथा नियमावली अनुसार गरिन्छ। यसमा कम्तीमा ३३% महिला प्रतिनिधित्व हुनुपर्ने कानूनी प्रावधान छ।",
            time: "2026-08-20T09:10:00Z",
            sources: [
              { documentName: "सहकारी ऐन, दफा ४१", provision: "सञ्चालक समिति गठन", id: "source-3" }
            ]
          }
        ]
      }
    ];
    localStorage.setItem('chatHistory', JSON.stringify(initialHistory));
    return initialHistory;
  });

  const [savedAnswers, setSavedAnswers] = useState(() => {
    const saved = localStorage.getItem('savedAnswers');
    if (saved) return JSON.parse(saved);

    // Initial mock saved answers
    const initialSaved = [
      {
        id: "save-1",
        question: "What are the core cooperative principles?",
        answer: "The 7 Cooperative Principles are: \n1. Voluntary and Open Membership\n2. Democratic Member Control\n3. Member Economic Participation\n4. Autonomy and Independence\n5. Education, Training, and Information\n6. Cooperation among Cooperatives\n7. Concern for Community.",
        category: "Getting Started",
        savedDate: "2026-08-29T11:00:00Z",
        sources: [
          { documentName: "International Cooperative Alliance Guidelines", provision: "Statement on Cooperative Identity", id: "source-1" }
        ]
      },
      {
        id: "save-2",
        question: "How is a cooperative dispute resolved?",
        answer: "Disputes in cooperatives should first be attempted to be resolved internally through the cooperative's Sub-Committee or Dispute Committee. If unresolved, they can be referred to the Cooperative Registrar or Arbitrators as per Section 98 of the Cooperative Act.",
        category: "Dispute Resolution",
        savedDate: "2026-08-27T16:45:00Z",
        sources: [
          { documentName: "Cooperative Act, Sec 98", provision: "Settlement of Disputes", id: "source-4" }
        ]
      }
    ];
    localStorage.setItem('savedAnswers', JSON.stringify(initialSaved));
    return initialSaved;
  });

  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3000);
  };

const addChatMessage = (chatId, message) => {
  setChatHistory(prevHistory => {
    const updatedHistory = prevHistory.map(chat => {
      if (chat.id === chatId) {
        return {
          ...chat,
          lastMessage: message.text,
          date: new Date().toISOString(),
          messages: [...chat.messages, message]
        };
      }

      return chat;
    });

    localStorage.setItem('chatHistory', JSON.stringify(updatedHistory));
    return updatedHistory;
  });
};

const createNewChat = (title, category, firstMessage = null) => {
  const newId = `chat-${Date.now()}`;

  const newChat = {
    id: newId,
    title: title || "New Conversation",
    lastMessage: firstMessage ? firstMessage.text : "No messages yet.",
    date: new Date().toISOString(),
    language: language,
    category: category || "General",
    messages: firstMessage ? [firstMessage] : []
  };

  setChatHistory(prevHistory => {
    const updatedHistory = [newChat, ...prevHistory];

    localStorage.setItem(
      'chatHistory',
      JSON.stringify(updatedHistory)
    );

    return updatedHistory;
  });

  return newId;
};

  const deleteChat = (chatId) => {
    const updatedHistory = chatHistory.filter(chat => chat.id !== chatId);
    setChatHistory(updatedHistory);
    localStorage.setItem('chatHistory', JSON.stringify(updatedHistory));
    showToast("Chat conversation deleted", "info");
  };

  const renameChat = (chatId, newTitle) => {
    const updatedHistory = chatHistory.map(chat => {
      if (chat.id === chatId) {
        return { ...chat, title: newTitle };
      }
      return chat;
    });
    setChatHistory(updatedHistory);
    localStorage.setItem('chatHistory', JSON.stringify(updatedHistory));
    showToast("Chat renamed successfully", "success");
  };

  const toggleSaveAnswer = (question, answer, category, sources) => {
    const alreadySaved = savedAnswers.find(sa => sa.question.toLowerCase() === question.toLowerCase());
    if (alreadySaved) {
      const updatedSaved = savedAnswers.filter(sa => sa.id !== alreadySaved.id);
      setSavedAnswers(updatedSaved);
      localStorage.setItem('savedAnswers', JSON.stringify(updatedSaved));
      showToast(t('removedFromBookmarks'), 'info');
      return false;
    } else {
      const newSaved = {
        id: `save-${Date.now()}`,
        question,
        answer,
        category: category || "General Guidance",
        savedDate: new Date().toISOString(),
        sources: sources || []
      };
      const updatedSaved = [newSaved, ...savedAnswers];
      setSavedAnswers(updatedSaved);
      localStorage.setItem('savedAnswers', JSON.stringify(updatedSaved));
      showToast(t('savedToBookmarks'), 'success');
      return true;
    }
  };

  const isAnswerSaved = (question) => {
    return !!savedAnswers.find(sa => sa.question.toLowerCase() === question.toLowerCase());
  };

  const clearAllChatHistory = () => {
    setChatHistory([]);
    localStorage.setItem('chatHistory', JSON.stringify([]));
    showToast("All chat history cleared", "info");
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      <ThemeContext.Provider value={{ theme, setTheme }}>
        <AccessibilityContext.Provider value={{ largerText, setLargerText, highContrast, setHighContrast }}>
          <AuthContext.Provider value={{ user, token, isGuest, login, register, completeAuthSession, logout, continueAsGuest, updateProfile }}>
            <AppDataContext.Provider value={{ 
              chatHistory, 
              savedAnswers, 
              toast, 
              showToast, 
              addChatMessage, 
              createNewChat, 
              deleteChat, 
              renameChat, 
              toggleSaveAnswer, 
              isAnswerSaved,
              clearAllChatHistory
            }}>
              {children}
            </AppDataContext.Provider>
          </AuthContext.Provider>
        </AccessibilityContext.Provider>
      </ThemeContext.Provider>
    </LanguageContext.Provider>
  );
};
