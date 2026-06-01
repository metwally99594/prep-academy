export default function MessageText({ content, selectedLang }) {
  return (
    <p className="whitespace-pre-wrap" style={{ direction: selectedLang === 'ar' ? 'rtl' : 'ltr' }}>{content}</p>
  );
}
