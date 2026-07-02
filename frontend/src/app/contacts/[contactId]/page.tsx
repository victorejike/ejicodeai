'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const ContactDetailPage = ({ params }: { params: { contactId: string } }) => {
  const { contactId } = params;
  const [contact, setContact] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchContact = async () => {
      const response = await fetch(`/api/contacts/${contactId}`);
      if (!response.ok) {
        setError('Unable to load contact details.');
        setLoading(false);
        return;
      }
      const data = await response.json();
      setContact(data);
      setLoading(false);
    };
    fetchContact();
  }, [contactId]);

  if (loading) {
    return <div className="container mx-auto px-4 py-6">Loading contact...</div>;
  }

  if (error) {
    return <div className="container mx-auto px-4 py-6">{error}</div>;
  }

  return (
    <main className="container mx-auto px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold">Contact Details</h1>
          <p className="text-gray-600">Review and manage individual contacts.</p>
        </div>
        <button
          onClick={() => router.back()}
          className="rounded-full border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
        >
          Back
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 p-6 shadow-sm bg-white">
        <h2 className="text-2xl font-semibold mb-3">{contact.full_name || contact.email}</h2>
        <div className="grid gap-4 md:grid-cols-2 text-sm text-slate-700">
          <div>
            <div className="font-semibold">Email</div>
            <div>{contact.email}</div>
          </div>
          <div>
            <div className="font-semibold">Title</div>
            <div>{contact.title || 'N/A'}</div>
          </div>
          <div>
            <div className="font-semibold">Company ID</div>
            <div>{contact.company_id || 'N/A'}</div>
          </div>
          <div>
            <div className="font-semibold">Status</div>
            <div>{contact.status || 'N/A'}</div>
          </div>
        </div>
      </div>
    </main>
  );
};

export default ContactDetailPage;
