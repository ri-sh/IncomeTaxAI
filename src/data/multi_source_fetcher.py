"""
Multi-Source Document Fetcher
Unified interface to fetch tax documents from multiple sources:
- Local folders (Documents/Tax Documents)
- Google Drive
- Manual upload
- Document scanner (future)
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import mimetypes
from datetime import datetime

try:
    from .google_drive_integration import GoogleDriveIntegration, DriveFile
    GDRIVE_AVAILABLE = True
except ImportError:
    print("⚠️  Google Drive integration dependencies not installed. Run: pip install -r requirements.txt")
    GoogleDriveIntegration = None
    DriveFile = None
    GDRIVE_AVAILABLE = False
from ..core.document_checklist import DocumentType, DocumentChecklist

class DocumentSource(Enum):
    """Source of the document"""
    LOCAL_FOLDER = "local_folder"
    GOOGLE_DRIVE = "google_drive"
    MANUAL_UPLOAD = "manual_upload"
    SCANNER = "scanner"

@dataclass
class SourceDocument:
    """Represents a document from any source"""
    path: str
    name: str
    source: DocumentSource
    file_type: str
    size: int
    modified_time: datetime
    detected_doc_type: Optional[DocumentType] = None
    confidence_score: float = 0.0

class DocumentClassifier:
    """Classifies documents based on filename and content patterns"""
    
    def __init__(self):
        self.patterns = {
            DocumentType.FORM_16: [
                'form 16', 'form16', 'tds certificate', 'salary certificate'
            ],
            DocumentType.FORM_16A: [
                'form 16a', 'form16a', 'tds other than salary'
            ],
            DocumentType.SALARY_SLIPS: [
                'salary slip', 'pay slip', 'payslip', 'salary statement'
            ],
            DocumentType.BANK_STATEMENTS: [
                'bank statement', 'account statement', 'savings account',
                'current account', 'statement of account'
            ],
            DocumentType.INTEREST_CERTIFICATES: [
                'interest certificate', 'bank interest', 'fd interest',
                'savings interest', 'deposit interest'
            ],
            DocumentType.LIC_PREMIUM_RECEIPTS: [
                'lic', 'life insurance', 'premium receipt', 'policy premium'
            ],
            DocumentType.ELSS_STATEMENTS: [
                'elss', 'equity linked', 'mutual fund', 'sip statement',
                'tax saving fund'
            ],
            DocumentType.PPF_STATEMENTS: [
                'ppf', 'public provident fund', 'ppf statement'
            ],
            DocumentType.EPF_STATEMENTS: [
                'epf', 'pf', 'provident fund', 'employee provident fund'
            ],
            DocumentType.HEALTH_INSURANCE_PREMIUM: [
                'health insurance', 'medical insurance', 'mediclaim',
                'health premium'
            ],
            DocumentType.HOME_LOAN_INTEREST: [
                'home loan', 'house loan', 'housing loan', 'loan interest',
                'interest certificate'
            ],
            DocumentType.RENT_RECEIPTS: [
                'rent receipt', 'house rent', 'rental receipt', 'hra receipt'
            ],
            DocumentType.CHARITABLE_DONATIONS: [
                'donation', 'charitable', 'charity receipt', '80g receipt'
            ],
            DocumentType.EDUCATION_LOAN_INTEREST: [
                'education loan', 'student loan', 'education interest'
            ],
            DocumentType.PAN_CARD: [
                'pan card', 'pan', 'permanent account number'
            ],
            DocumentType.AADHAAR_CARD: [
                'aadhaar', 'aadhar', 'uidai'
            ]
        }
    
    def classify_document(self, filename: str) -> Tuple[Optional[DocumentType], float]:
        """Classify document based on filename"""
        filename_lower = filename.lower()
        
        best_match = None
        best_score = 0.0
        
        for doc_type, patterns in self.patterns.items():
            score = 0.0
            for pattern in patterns:
                if pattern in filename_lower:
                    # Full pattern match gets higher score
                    score += len(pattern) / len(filename_lower)
            
            if score > best_score:
                best_score = score
                best_match = doc_type
        
        # Only return if confidence is reasonable
        if best_score > 0.1:
            return best_match, min(best_score, 1.0)
        
        return None, 0.0

class MultiSourceDocumentFetcher:
    """Fetches and manages documents from multiple sources"""
    
    def __init__(self, local_base_path: str = None):
        self.local_base_path = local_base_path or str(Path.home() / "Desktop" / "Income Tax 2024-2025")
        self._gdrive = None  # Lazy load Google Drive integration
        self.classifier = DocumentClassifier()
        self.checklist = DocumentChecklist()
        
        # Supported file types
        self.supported_extensions = {'.pdf', '.xlsx', '.xls', '.csv', '.jpg', '.jpeg', '.png', '.tiff'}
    
    @property
    def gdrive(self):
        """Lazy load Google Drive integration only when needed"""
        if self._gdrive is None and GDRIVE_AVAILABLE:
            self._gdrive = GoogleDriveIntegration()
        return self._gdrive
        
    def scan_local_folder(self, folder_path: Optional[str] = None) -> List[SourceDocument]:
        """Scan local folder for tax documents"""
        scan_path = folder_path or self.local_base_path
        documents = []
        
        if not os.path.exists(scan_path):
            print(f"ℹ️  Local folder not found: {scan_path}")
            return documents
        
        print(f"📁 Scanning local folder: {scan_path}")
        
        for root, dirs, files in os.walk(scan_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file).suffix.lower()
                
                if file_ext in self.supported_extensions:
                    try:
                        stat = os.stat(file_path)
                        doc_type, confidence = self.classifier.classify_document(file)
                        
                        document = SourceDocument(
                            path=file_path,
                            name=file,
                            source=DocumentSource.LOCAL_FOLDER,
                            file_type=file_ext,
                            size=stat.st_size,
                            modified_time=datetime.fromtimestamp(stat.st_mtime),
                            detected_doc_type=doc_type,
                            confidence_score=confidence
                        )
                        documents.append(document)
                        
                        # Mark in checklist if detected
                        if doc_type:
                            self.checklist.mark_document_found(doc_type)
                            
                    except Exception as e:
                        print(f"⚠️  Error processing {file}: {str(e)}")
        
        print(f"✅ Found {len(documents)} documents in local folder")
        return documents
    
    def fetch_from_google_drive(self, folder_name: Optional[str] = None) -> List[SourceDocument]:
        """Fetch tax documents from Google Drive"""
        documents = []
        
        if not GDRIVE_AVAILABLE or not self.gdrive:
            print("❌ Google Drive integration not available. Install dependencies with: pip install -r requirements.txt")
            return documents
        
        if not self.gdrive.authenticate():
            print("❌ Cannot authenticate with Google Drive")
            return documents
        
        print("☁️  Fetching documents from Google Drive...")
        
        # Search for tax documents
        drive_files = self.gdrive.search_tax_documents(folder_name)
        
        # Download files to temporary location
        temp_folder = "./data/temp_gdrive"
        os.makedirs(temp_folder, exist_ok=True)
        
        for drive_file in drive_files:
            try:
                # Create safe local filename
                safe_name = "".join(c for c in drive_file.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                local_path = os.path.join(temp_folder, safe_name)
                
                # Download file
                if self.gdrive.download_file(drive_file.id, local_path):
                    doc_type, confidence = self.classifier.classify_document(drive_file.name)
                    
                    document = SourceDocument(
                        path=local_path,
                        name=drive_file.name,
                        source=DocumentSource.GOOGLE_DRIVE,
                        file_type=Path(drive_file.name).suffix.lower(),
                        size=drive_file.size or 0,
                        modified_time=datetime.fromisoformat(drive_file.modified_time.replace('Z', '+00:00')),
                        detected_doc_type=doc_type,
                        confidence_score=confidence
                    )
                    documents.append(document)
                    
                    # Mark in checklist if detected
                    if doc_type:
                        self.checklist.mark_document_found(doc_type)
                        
            except Exception as e:
                print(f"⚠️  Error processing Google Drive file {drive_file.name}: {str(e)}")
        
        print(f"✅ Fetched {len(documents)} documents from Google Drive")
        return documents
    
    def process_manual_upload(self, uploaded_files: List[str]) -> List[SourceDocument]:
        """Process manually uploaded files"""
        documents = []
        
        for file_path in uploaded_files:
            if not os.path.exists(file_path):
                continue
                
            try:
                file_name = os.path.basename(file_path)
                file_ext = Path(file_name).suffix.lower()
                
                if file_ext in self.supported_extensions:
                    stat = os.stat(file_path)
                    doc_type, confidence = self.classifier.classify_document(file_name)
                    
                    document = SourceDocument(
                        path=file_path,
                        name=file_name,
                        source=DocumentSource.MANUAL_UPLOAD,
                        file_type=file_ext,
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        detected_doc_type=doc_type,
                        confidence_score=confidence
                    )
                    documents.append(document)
                    
                    # Mark in checklist if detected
                    if doc_type:
                        self.checklist.mark_document_found(doc_type)
                        
            except Exception as e:
                print(f"⚠️  Error processing uploaded file {file_path}: {str(e)}")
        
        print(f"✅ Processed {len(documents)} manually uploaded files")
        return documents
    
    def fetch_all_documents(self, 
                          include_local: bool = True,
                          include_gdrive: bool = True,
                          gdrive_folder: Optional[str] = None,
                          uploaded_files: Optional[List[str]] = None) -> Dict[str, List[SourceDocument]]:
        """Fetch documents from all enabled sources"""
        all_documents = {
            'local': [],
            'google_drive': [],
            'manual_upload': []
        }
        
        # Reset checklist for fresh scan
        self.checklist = DocumentChecklist()
        
        if include_local:
            all_documents['local'] = self.scan_local_folder()
        
        if include_gdrive:
            all_documents['google_drive'] = self.fetch_from_google_drive(gdrive_folder)
        
        if uploaded_files:
            all_documents['manual_upload'] = self.process_manual_upload(uploaded_files)
        
        return all_documents
    
    def get_document_summary(self, documents: Dict[str, List[SourceDocument]]) -> Dict:
        """Get comprehensive summary of fetched documents"""
        total_docs = sum(len(docs) for docs in documents.values())
        
        # Count by document type
        type_counts = {}
        confidence_stats = []
        
        for source_docs in documents.values():
            for doc in source_docs:
                if doc.detected_doc_type:
                    type_counts[doc.detected_doc_type] = type_counts.get(doc.detected_doc_type, 0) + 1
                    confidence_stats.append(doc.confidence_score)
        
        # Get missing documents analysis
        checklist_summary = self.checklist.get_document_checklist_summary()
        
        return {
            'total_documents': total_docs,
            'documents_by_source': {source: len(docs) for source, docs in documents.items()},
            'documents_by_type': {doc_type.value: count for doc_type, count in type_counts.items()},
            'average_confidence': sum(confidence_stats) / len(confidence_stats) if confidence_stats else 0,
            'checklist_summary': checklist_summary,
            'recommendations': self._generate_recommendations(documents, checklist_summary)
        }
    
    def _generate_recommendations(self, documents: Dict[str, List[SourceDocument]], 
                                checklist_summary: Dict) -> List[str]:
        """Generate recommendations based on found and missing documents"""
        recommendations = []
        
        total_docs = sum(len(docs) for docs in documents.values())
        
        if total_docs == 0:
            recommendations.append("🔍 No tax documents found. Please check your folder paths and Google Drive access.")
            return recommendations
        
        # Source recommendations
        if not documents['local']:
            recommendations.append(f"📁 Consider organizing documents in local folder: {self.local_base_path}")
        
        if not documents['google_drive']:
            recommendations.append("☁️  Connect Google Drive to access cloud-stored tax documents")
        
        # Missing document recommendations
        completion = checklist_summary['completion_percentage']
        if completion < 50:
            recommendations.append(f"⚠️  Document collection is {completion:.0f}% complete. Focus on mandatory documents first.")
        elif completion < 80:
            recommendations.append(f"👍 Good progress! {completion:.0f}% complete. Add recommended documents to maximize tax savings.")
        else:
            recommendations.append(f"🎉 Excellent! {completion:.0f}% complete. You have most required documents.")
        
        # Low confidence warnings
        low_confidence_docs = []
        for source_docs in documents.values():
            for doc in source_docs:
                if doc.confidence_score < 0.3:
                    low_confidence_docs.append(doc.name)
        
        if low_confidence_docs:
            recommendations.append(f"🔍 Please verify these documents manually: {', '.join(low_confidence_docs[:3])}")
        
        return recommendations
    
    def organize_documents(self, documents: Dict[str, List[SourceDocument]], 
                         output_folder: str = "./data/organized_documents") -> Dict[str, str]:
        """Organize documents by type in structured folders"""
        organized_paths = {}
        
        # Create organized folder structure
        type_folders = {
            DocumentType.FORM_16: "01_Salary_Documents",
            DocumentType.FORM_16A: "01_Salary_Documents", 
            DocumentType.SALARY_SLIPS: "01_Salary_Documents",
            DocumentType.BANK_STATEMENTS: "02_Bank_Documents",
            DocumentType.INTEREST_CERTIFICATES: "02_Bank_Documents",
            DocumentType.LIC_PREMIUM_RECEIPTS: "03_Insurance",
            DocumentType.HEALTH_INSURANCE_PREMIUM: "03_Insurance",
            DocumentType.ELSS_STATEMENTS: "04_Investments",
            DocumentType.PPF_STATEMENTS: "04_Investments",
            DocumentType.EPF_STATEMENTS: "04_Investments",
            DocumentType.HOME_LOAN_INTEREST: "05_House_Property",
            DocumentType.RENT_RECEIPTS: "05_House_Property",
            DocumentType.CHARITABLE_DONATIONS: "06_Deductions",
            DocumentType.EDUCATION_LOAN_INTEREST: "06_Deductions",
            DocumentType.PAN_CARD: "07_Identity_Documents",
            DocumentType.AADHAAR_CARD: "07_Identity_Documents"
        }
        
        for source_docs in documents.values():
            for doc in source_docs:
                try:
                    if doc.detected_doc_type and doc.detected_doc_type in type_folders:
                        folder_name = type_folders[doc.detected_doc_type]
                        dest_folder = os.path.join(output_folder, folder_name)
                        os.makedirs(dest_folder, exist_ok=True)
                        
                        dest_path = os.path.join(dest_folder, doc.name)
                        shutil.copy2(doc.path, dest_path)
                        organized_paths[doc.path] = dest_path
                    else:
                        # Unclassified documents
                        unclassified_folder = os.path.join(output_folder, "99_Unclassified")
                        os.makedirs(unclassified_folder, exist_ok=True)
                        dest_path = os.path.join(unclassified_folder, doc.name)
                        shutil.copy2(doc.path, dest_path)
                        organized_paths[doc.path] = dest_path
                        
                except Exception as e:
                    print(f"⚠️  Error organizing {doc.name}: {str(e)}")
        
        print(f"✅ Organized {len(organized_paths)} documents")
        return organized_paths

# Example usage
if __name__ == "__main__":
    fetcher = MultiSourceDocumentFetcher()
    
    # Fetch from all sources
    documents = fetcher.fetch_all_documents(
        include_local=True,
        include_gdrive=True,
        gdrive_folder="Income Tax 2024-2025"
    )
    
    # Get summary
    summary = fetcher.get_document_summary(documents)
    print(f"📊 Found {summary['total_documents']} documents")
    print(f"📈 Checklist completion: {summary['checklist_summary']['completion_percentage']:.1f}%")
    
    # Show recommendations
    for rec in summary['recommendations']:
        print(rec)