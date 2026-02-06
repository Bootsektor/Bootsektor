import logging
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class LearningDatabase:
    """Learning database for content relevance prediction and optimization"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Database configuration
        self.db_path = Path(config.get('database.path', 'data/scanner.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Machine learning components
        self.vectorizer = None
        self.classifier = None
        self.model_trained = False
        
        # Initialize database
        self._init_database()
        
        # Load or train model
        self._load_or_train_model()
    
    def _init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Articles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        image_url TEXT,
                        link TEXT,
                        source_url TEXT,
                        scraped_at TIMESTAMP,
                        relevance_score REAL,
                        user_interest INTEGER,
                        keywords TEXT,
                        processed BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # User feedback table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        article_id INTEGER,
                        feedback_type TEXT,  -- 'interested', 'not_interested', 'clicked'
                        feedback_timestamp TIMESTAMP,
                        FOREIGN KEY (article_id) REFERENCES articles (id)
                    )
                ''')
                
                # Performance metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT,
                        metric_value REAL,
                        timestamp TIMESTAMP
                    )
                ''')
                
                # Keyword effectiveness table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS keyword_effectiveness (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT,
                        success_count INTEGER,
                        total_count INTEGER,
                        effectiveness_score REAL,
                        last_updated TIMESTAMP
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def _load_or_train_model(self):
        """Load existing model or train new one"""
        try:
            # Try to load existing model
            if self._load_model():
                self.logger.info("Loaded existing learning model")
            else:
                # Train new model if enough data exists
                if self._has_enough_training_data():
                    self._train_model()
                else:
                    self.logger.info("Not enough data for training, using basic filtering")
        except Exception as e:
            self.logger.error(f"Error with model loading/training: {e}")
    
    async def record_article(self, article: Dict[str, Any]):
        """Record article in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate initial relevance score
                relevance_score = self._calculate_relevance_score(article)
                
                # Extract keywords
                keywords = self._extract_keywords(article)
                
                cursor.execute('''
                    INSERT INTO articles 
                    (title, content, image_url, link, source_url, scraped_at, 
                     relevance_score, keywords, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.get('title', ''),
                    article.get('cleaned_content', ''),
                    article.get('image_url', ''),
                    article.get('link', ''),
                    article.get('source_url', ''),
                    article.get('scraped_at', ''),
                    relevance_score,
                    json.dumps(keywords),
                    False
                ))
                
                conn.commit()
                self.logger.debug(f"Recorded article: {article.get('title', '')[:50]}...")
                
        except Exception as e:
            self.logger.error(f"Error recording article: {e}")
    
    async def record_user_feedback(self, article_id: int, feedback_type: str):
        """Record user feedback for learning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Record feedback
                cursor.execute('''
                    INSERT INTO user_feedback 
                    (article_id, feedback_type, feedback_timestamp)
                    VALUES (?, ?, ?)
                ''', (article_id, feedback_type, datetime.now().isoformat()))
                
                # Update article with user interest
                if feedback_type == 'interested':
                    user_interest = 1
                elif feedback_type == 'not_interested':
                    user_interest = 0
                else:
                    user_interest = None
                
                if user_interest is not None:
                    cursor.execute('''
                        UPDATE articles SET user_interest = ? WHERE id = ?
                    ''', (user_interest, article_id))
                
                conn.commit()
                
                # Retrain model if we have enough new data
                if self._should_retrain():
                    self._train_model()
                
                self.logger.info(f"Recorded feedback: {feedback_type} for article {article_id}")
                
        except Exception as e:
            self.logger.error(f"Error recording user feedback: {e}")
    
    async def predict_interest(self, article: Dict[str, Any]) -> bool:
        """Predict if user will be interested in article"""
        try:
            if not self.model_trained:
                # Fallback to basic keyword matching
                return self._basic_interest_prediction(article)
            
            # Use trained model
            text = f"{article.get('title', '')} {article.get('cleaned_content', '')}"
            
            # Vectorize text
            text_vector = self.vectorizer.transform([text])
            
            # Predict
            prediction = self.classifier.predict(text_vector)[0]
            probability = self.classifier.predict_proba(text_vector)[0]
            
            # Log prediction confidence
            confidence = max(probability)
            self.logger.debug(f"Interest prediction: {prediction} (confidence: {confidence:.2f})")
            
            return prediction == 1
            
        except Exception as e:
            self.logger.error(f"Error predicting interest: {e}")
            return self._basic_interest_prediction(article)
    
    def _basic_interest_prediction(self, article: Dict[str, Any]) -> bool:
        """Basic interest prediction using keywords"""
        try:
            # Get keywords from config
            keywords = self.config.get('content_filter.keywords', [])
            blacklist = self.config.get('content_filter.blacklist', [])
            
            title = article.get('title', '').lower()
            content = article.get('cleaned_content', '').lower()
            combined_text = f"{title} {content}"
            
            # Check blacklist
            for term in blacklist:
                if term.lower() in combined_text:
                    return False
            
            # Check keywords
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in basic interest prediction: {e}")
            return False
    
    def _calculate_relevance_score(self, article: Dict[str, Any]) -> float:
        """Calculate relevance score for article"""
        try:
            # Factors for relevance score
            title = article.get('title', '')
            content = article.get('cleaned_content', '')
            
            score = 0.0
            
            # Title length factor
            title_length = len(title)
            if 20 <= title_length <= 100:
                score += 0.2
            
            # Content length factor
            content_length = len(content)
            if content_length > 200:
                score += 0.2
            
            # Keyword presence
            keywords = self.config.get('content_filter.keywords', [])
            keyword_matches = sum(1 for keyword in keywords 
                                  if keyword.lower() in f"{title} {content}".lower())
            if keywords:
                score += (keyword_matches / len(keywords)) * 0.4
            
            # Image presence
            if article.get('image_url'):
                score += 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.0
    
    def _extract_keywords(self, article: Dict[str, Any]) -> List[str]:
        """Extract keywords from article"""
        try:
            from sklearn.feature_extraction.text import CountVectorizer
            
            text = f"{article.get('title', '')} {article.get('cleaned_content', '')}"
            
            # Simple keyword extraction
            vectorizer = CountVectorizer(max_features=10, stop_words='english')
            try:
                vectorizer.fit_transform([text])
                return vectorizer.get_feature_names_out().tolist()
            except:
                # Fallback to simple word extraction
                words = text.lower().split()
                # Filter out common words
                common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
                keywords = [word for word in words if word not in common_words and len(word) > 3]
                return keywords[:10]
                
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            return []
    
    def _has_enough_training_data(self) -> bool:
        """Check if there's enough data for training"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM articles 
                    WHERE user_interest IS NOT NULL
                ''')
                count = cursor.fetchone()[0]
                return count >= 50  # Minimum 50 labeled examples
                
        except Exception as e:
            self.logger.error(f"Error checking training data: {e}")
            return False
    
    def _train_model(self):
        """Train machine learning model"""
        try:
            # Get training data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT title, content, user_interest 
                    FROM articles 
                    WHERE user_interest IS NOT NULL
                ''')
                
                data = cursor.fetchall()
                
            if len(data) < 50:
                self.logger.warning("Not enough data for training")
                return
            
            # Prepare training data
            texts = []
            labels = []
            
            for title, content, user_interest in data:
                text = f"{title} {content}"
                texts.append(text)
                labels.append(user_interest)
            
            # Vectorize text
            self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
            X = self.vectorizer.fit_transform(texts)
            y = np.array(labels)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train classifier
            self.classifier = MultinomialNB()
            self.classifier.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.classifier.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.logger.info(f"Model trained with accuracy: {accuracy:.2f}")
            self.model_trained = True
            
            # Save model
            self._save_model()
            
            # Record performance
            self._record_performance_metric('model_accuracy', accuracy)
            
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
    
    def _load_model(self) -> bool:
        """Load saved model"""
        try:
            model_file = self.db_path.parent / 'model.json'
            if model_file.exists():
                with open(model_file, 'r') as f:
                    model_data = json.load(f)
                
                # Note: In a real implementation, you'd use joblib or pickle
                # For simplicity, we're just checking if model exists
                self.model_trained = True
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    def _save_model(self):
        """Save trained model"""
        try:
            model_file = self.db_path.parent / 'model.json'
            model_data = {
                'trained_at': datetime.now().isoformat(),
                'model_type': 'naive_bayes'
            }
            
            with open(model_file, 'w') as f:
                json.dump(model_data, f)
            
            self.logger.info("Model saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
    
    def _should_retrain(self) -> bool:
        """Check if model should be retrained"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM user_feedback 
                    WHERE feedback_timestamp > datetime('now', '-1 day')
                ''')
                recent_feedback = cursor.fetchone()[0]
                
                return recent_feedback >= 10  # Retrain after 10 new feedback entries
                
        except Exception as e:
            self.logger.error(f"Error checking retrain condition: {e}")
            return False
    
    def _record_performance_metric(self, metric_name: str, value: float):
        """Record performance metric"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO performance_metrics 
                    (metric_name, metric_value, timestamp)
                    VALUES (?, ?, ?)
                ''', (metric_name, value, datetime.now().isoformat()))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording performance metric: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total articles
                cursor.execute('SELECT COUNT(*) FROM articles')
                stats['total_articles'] = cursor.fetchone()[0]
                
                # Articles with user feedback
                cursor.execute('SELECT COUNT(*) FROM articles WHERE user_interest IS NOT NULL')
                stats['articles_with_feedback'] = cursor.fetchone()[0]
                
                # User interest rate
                cursor.execute('''
                    SELECT AVG(user_interest) FROM articles 
                    WHERE user_interest IS NOT NULL
                ''')
                avg_interest = cursor.fetchone()[0]
                stats['user_interest_rate'] = avg_interest if avg_interest else 0
                
                # Recent activity
                cursor.execute('''
                    SELECT COUNT(*) FROM articles 
                    WHERE scraped_at > datetime('now', '-24 hours')
                ''')
                stats['articles_last_24h'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}