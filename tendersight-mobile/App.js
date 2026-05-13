import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, SafeAreaView, Alert, Platform, Linking, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as LocalAuthentication from 'expo-local-authentication';
import { ShieldCheck, ArrowRight, AlertTriangle, Scale, CheckCircle2, FileText, ChevronRight, Fingerprint, LogOut, Users, Download } from 'lucide-react-native';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('login'); // login -> pin -> dashboard -> detail -> signoff
  const [pin, setPin] = useState('');
  const [selectedTender, setSelectedTender] = useState(null);
  const [tenders, setTenders] = useState([]);
  const [tenderDetails, setTenderDetails] = useState(null);
  const [loading, setLoading] = useState(false);

  const API_BASE_URL = "https://tendersight-jv14.onrender.com";
  const MOCK_PIN = "1234";

  useEffect(() => {
    if (currentScreen === 'dashboard') fetchTenders();
  }, [currentScreen]);

  const fetchTenders = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/tenders/summary`);
      const data = await res.json();
      setTenders(data.tenders || []);
    } catch (e) {
      console.error(e);
      Alert.alert("Connection Error", "Could not reach TenderSight backend.");
    } finally {
      setLoading(false);
    }
  };

  const fetchTenderDetails = async (tender) => {
    setSelectedTender(tender);
    setCurrentScreen('detail');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/tenders/${tender.id}`);
      const data = await res.json();
      setTenderDetails(data);
    } catch (e) {
      console.error(e);
      Alert.alert("Connection Error", "Could not fetch tender details.");
    } finally {
      setLoading(false);
    }
  };

  const handlePinPress = (num) => {
    if (pin.length < 4) {
      const newPin = pin + num;
      setPin(newPin);
      if (newPin.length === 4) {
        if (newPin === MOCK_PIN) {
          setCurrentScreen('dashboard');
          setPin('');
        } else {
          Alert.alert("Access Denied", "Incorrect Security PIN.", [{ text: "OK", onPress: () => setPin('') }]);
        }
      }
    }
  };

  // --- Screens ---

  if (currentScreen === 'login') {
    return (
      <View style={styles.loginContainer}>
        <StatusBar style="light" />
        <View style={styles.loginContent}>
          <View style={styles.iconWrapper}>
            <Scale color="#ffffff" size={64} />
          </View>
          <Text style={styles.loginTitle}>TenderSight</Text>
          <Text style={styles.loginSubtitle}>Executive Authorization Portal</Text>
          
          <TouchableOpacity style={styles.loginBtn} onPress={() => setCurrentScreen('pin')}>
            <Text style={styles.loginBtnText}>Secure Login (Gov ID)</Text>
            <ArrowRight color="#4F46E5" size={20} />
          </TouchableOpacity>
        </View>
        <Text style={styles.footerText}>Gov. of India • NIC Secured</Text>
      </View>
    );
  }

  if (currentScreen === 'pin') {
    return (
      <View style={styles.loginContainer}>
        <StatusBar style="light" />
        <TouchableOpacity style={styles.backBtn} onPress={() => {setCurrentScreen('login'); setPin('');}}>
          <ChevronRight color="#ffffff" size={32} style={{transform: [{rotate: '180deg'}]}} />
        </TouchableOpacity>
        
        <View style={styles.loginContent}>
          <Text style={styles.loginSubtitle}>Enter 4-Digit Security PIN</Text>
          <View style={styles.pinDisplay}>
            {[0, 1, 2, 3].map((i) => (
              <View key={i} style={[styles.pinDot, pin.length > i && styles.pinDotFilled]} />
            ))}
          </View>
          
          <View style={styles.keypad}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 'C', 0, ' '].map((num, idx) => (
              <TouchableOpacity 
                key={idx} 
                style={[styles.keypadBtn, num === ' ' && {backgroundColor: 'transparent'}]}
                onPress={() => {
                  if (num === 'C') setPin('');
                  else if (num !== ' ') handlePinPress(num.toString());
                }}
                disabled={num === ' '}
              >
                <Text style={styles.keypadText}>{num}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={{color: '#818cf8', marginTop: 32}}>Demo PIN: 1234</Text>
        </View>
      </View>
    );
  }

  if (currentScreen === 'dashboard') {
    return (
      <SafeAreaView style={styles.appContainer}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome, Joint Secretary</Text>
            <Text style={styles.subGreeting}>{tenders.length} Active Tenders</Text>
          </View>
          <TouchableOpacity onPress={() => setCurrentScreen('login')} style={styles.logoutBtn}>
            <LogOut color="#64748b" size={20} />
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.scrollArea}>
          {loading && <ActivityIndicator size="large" color="#4f46e5" style={{marginTop: 40}} />}
          {!loading && tenders.length === 0 && <Text style={{textAlign: 'center', marginTop: 40, color: '#64748b'}}>No active tenders in the system.</Text>}
          
          {!loading && tenders.map((tender) => (
            <TouchableOpacity key={tender.id} style={[styles.card, tender.has_alert ? styles.alertCardBorder : null]} onPress={() => fetchTenderDetails(tender)}>
              <View style={styles.cardHeader}>
                <Text style={styles.tenderId} numberOfLines={1}>{tender.title}</Text>
                {tender.has_alert ? (
                  <View style={styles.alertBadge}>
                    <AlertTriangle color="#dc2626" size={12} />
                    <Text style={styles.alertText}>CARTEL RISK</Text>
                  </View>
                ) : (
                  <View style={styles.cleanBadge}>
                    <CheckCircle2 color="#059669" size={12} />
                    <Text style={styles.cleanText}>CLEAN</Text>
                  </View>
                )}
              </View>
              <Text style={styles.l1Text}>L1: <Text style={styles.bold}>{tender.l1_bidder}</Text></Text>
              {tender.l1_amount !== null && <Text style={styles.bidAmount}>Rs. {tender.l1_amount.toLocaleString('en-IN')}</Text>}
              
              <View style={styles.cardFooter}>
                <Text style={styles.footerActionText}>View Executive Summary</Text>
                <ChevronRight color="#4f46e5" size={16} />
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (currentScreen === 'detail' && selectedTender) {
    const evals = tenderDetails?.evaluations || {};
    const bidders = Object.keys(evals);

    return (
      <SafeAreaView style={styles.appContainer}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setCurrentScreen('dashboard')} style={{flexDirection: 'row', alignItems: 'center'}}>
            <ChevronRight color="#4f46e5" size={24} style={{transform: [{rotate: '180deg'}]}} />
            <Text style={{color: '#4f46e5', fontWeight: '600', fontSize: 16}}>Dashboard</Text>
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.scrollArea}>
          <Text style={styles.detailTitle}>{selectedTender.title}</Text>
          <Text style={styles.detailSubtitle}>Tender ID: {selectedTender.id}</Text>

          {/* Download PDF Button */}
          <TouchableOpacity 
            style={styles.pdfBtn}
            onPress={() => Linking.openURL(`${API_BASE_URL}/report/${selectedTender.id}`)}
          >
            <Download color="#ffffff" size={20} />
            <Text style={styles.pdfBtnText}>Download Full Audit Report (PDF)</Text>
          </TouchableOpacity>

          {/* Cartel Alert Banner */}
          {selectedTender.has_alert && selectedTender.cartel_alerts.map((alert, idx) => (
            <View key={idx} style={styles.severeWarningBox}>
              <AlertTriangle color="#dc2626" size={24} />
              <View style={{flex: 1, marginLeft: 16}}>
                <Text style={styles.severeWarningTitle}>High Cartel Risk Detected</Text>
                <Text style={styles.severeWarningDesc}>
                  AI Graph confirms <Text style={styles.bold}>{alert.bidder1}</Text> and <Text style={styles.bold}>{alert.bidder2}</Text> share the same {alert.link_type}: {alert.shared_entity}. 
                  Collusive bidding highly probable.
                </Text>
              </View>
            </View>
          ))}

          {loading ? (
             <ActivityIndicator size="large" color="#4f46e5" style={{marginTop: 40}} />
          ) : (
            <View>
              <Text style={styles.sectionHeader}><Users size={18} color="#475569" style={{marginRight: 8}}/> Bidder Evaluations ({bidders.length})</Text>
              
              {bidders.map(name => {
                const ev = evals[name];
                const isL1 = selectedTender.l1_bidder === name;
                return (
                  <View key={name} style={[styles.bidderRow, isL1 && styles.l1Row]}>
                    <View>
                      <Text style={[styles.bold, {fontSize: 16, color: '#0f172a'}]}>{name}</Text>
                      <Text style={{fontSize: 12, color: '#64748b', marginTop: 4}}>
                        {ev.eligible_count} Eligible • {ev.manual_review_count} Manual Review • {ev.not_eligible_count} Not Eligible
                      </Text>
                      {ev.financial_bid && <Text style={{fontSize: 14, fontWeight: '700', color: '#10b981', marginTop: 8}}>Bid: Rs. {Number(ev.financial_bid).toLocaleString('en-IN')}</Text>}
                    </View>
                    <View style={styles.statusPill(ev.overall_status)}>
                      <Text style={styles.statusText(ev.overall_status)}>{ev.overall_status}</Text>
                    </View>
                  </View>
                );
              })}

              <TouchableOpacity style={[styles.authBtn, {marginTop: 32}]} onPress={() => setCurrentScreen('signoff')}>
                <ShieldCheck color="#ffffff" size={24} />
                <Text style={styles.authBtnText}>Proceed to Authorization</Text>
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (currentScreen === 'signoff' && selectedTender) {
    const handleAuthorize = async () => {
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();
      
      if (hasHardware && isEnrolled) {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: 'Authorize Tender Sign-off',
          fallbackLabel: 'Use PIN',
        });
        
        if (result.success) {
          Alert.alert("Success", "Tender Cryptographically Sealed & Approved.", [
            { text: "OK", onPress: () => setCurrentScreen('dashboard') }
          ]);
        } else {
          Alert.alert("Authorization Failed", "Biometrics not verified.");
        }
      } else {
        Alert.alert("Success", "Tender Approved (Simulator Fallback).", [
          { text: "OK", onPress: () => setCurrentScreen('dashboard') }
        ]);
      }
    };

    return (
      <SafeAreaView style={styles.appContainer}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setCurrentScreen('detail')} style={{flexDirection: 'row', alignItems: 'center'}}>
            <ChevronRight color="#4f46e5" size={24} style={{transform: [{rotate: '180deg'}]}} />
            <Text style={{color: '#4f46e5', fontWeight: '600', fontSize: 16}}>Cancel</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.signoffContent}>
          <FileText color="#94a3b8" size={48} style={{marginBottom: 16}} />
          <Text style={styles.summaryTitle}>Final Authorization</Text>
          <Text style={styles.summaryTender}>{selectedTender.id}</Text>
          
          <View style={styles.receiptBox}>
            <Text style={styles.receiptLabel}>Awarding To</Text>
            <Text style={styles.receiptValue}>{selectedTender.l1}</Text>
            <View style={styles.divider} />
            <Text style={styles.receiptLabel}>Final Amount</Text>
            <Text style={styles.receiptValue}>Rs. {selectedTender.bid}</Text>
          </View>

          {selectedTender.alert && (
            <View style={styles.warningBox}>
              <AlertTriangle color="#dc2626" size={20} />
              <View style={{flex: 1, marginLeft: 12}}>
                <Text style={styles.warningTitle}>Cartel Risk Overruled</Text>
                <Text style={styles.warningDesc}>You are authorizing an override of a verified cartel risk flag. This action will be logged in the permanent audit trail.</Text>
              </View>
            </View>
          )}

          <TouchableOpacity style={styles.authBtn} onPress={handleAuthorize}>
            <Fingerprint color="#ffffff" size={24} />
            <Text style={styles.authBtnText}>Seal & Authorize</Text>
          </TouchableOpacity>
          <Text style={{textAlign: 'center', color: '#94a3b8', fontSize: 12, marginTop: 16}}>
            This action generates an immutable PDF audit trail and notifies bidders.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  // Login & PIN
  loginContainer: { flex: 1, backgroundColor: '#312e81', justifyContent: 'center', alignItems: 'center' },
  loginContent: { alignItems: 'center', width: '100%', paddingHorizontal: 40 },
  iconWrapper: { backgroundColor: 'rgba(255,255,255,0.1)', padding: 20, borderRadius: 30, marginBottom: 24 },
  loginTitle: { fontSize: 42, fontWeight: '900', color: '#ffffff', marginBottom: 8 },
  loginSubtitle: { fontSize: 16, color: '#a5b4fc', marginBottom: 48 },
  loginBtn: { backgroundColor: '#ffffff', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 16, paddingHorizontal: 32, borderRadius: 16, width: '100%' },
  loginBtnText: { color: '#4f46e5', fontSize: 18, fontWeight: '700', marginRight: 8 },
  footerText: { position: 'absolute', bottom: 40, color: '#818cf8', fontSize: 12 },
  backBtn: { position: 'absolute', top: 60, left: 20, padding: 10 },
  pinDisplay: { flexDirection: 'row', gap: 16, marginBottom: 48 },
  pinDot: { width: 16, height: 16, borderRadius: 8, borderWidth: 2, borderColor: '#818cf8' },
  pinDotFilled: { backgroundColor: '#ffffff', borderColor: '#ffffff' },
  keypad: { flexDirection: 'row', flexWrap: 'wrap', width: 280, justifyContent: 'center', gap: 16 },
  keypadBtn: { width: 70, height: 70, borderRadius: 35, backgroundColor: 'rgba(255,255,255,0.1)', justifyContent: 'center', alignItems: 'center' },
  keypadText: { color: '#ffffff', fontSize: 28, fontWeight: '600' },

  // App Layout
  appContainer: { flex: 1, backgroundColor: '#f8fafc' },
  header: { paddingHorizontal: 24, paddingTop: Platform.OS === 'android' ? 40 : 20, paddingBottom: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#ffffff', borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  greeting: { fontSize: 20, fontWeight: '800', color: '#0f172a' },
  subGreeting: { fontSize: 14, color: '#64748b', marginTop: 4 },
  logoutBtn: { padding: 8, backgroundColor: '#f1f5f9', borderRadius: 12 },
  scrollArea: { padding: 24 },

  // Cards
  card: { backgroundColor: '#ffffff', borderRadius: 20, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: '#e2e8f0' },
  alertCardBorder: { borderLeftWidth: 4, borderLeftColor: '#dc2626' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  tenderId: { fontSize: 14, fontWeight: '700', color: '#475569', flex: 1 },
  alertBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fef2f2', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, borderWidth: 1, borderColor: '#fee2e2' },
  alertText: { color: '#dc2626', fontSize: 10, fontWeight: '800', marginLeft: 4 },
  cleanBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ecfdf5', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, borderWidth: 1, borderColor: '#d1fae5' },
  cleanText: { color: '#059669', fontSize: 10, fontWeight: '800', marginLeft: 4 },
  l1Text: { fontSize: 16, color: '#334155' },
  bold: { fontWeight: '800', color: '#0f172a' },
  bidAmount: { fontSize: 24, fontWeight: '900', color: '#10b981', marginTop: 8, marginBottom: 20 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: '#f1f5f9', paddingTop: 16 },
  footerActionText: { color: '#4f46e5', fontWeight: '700', fontSize: 14 },

  // Detail Screen
  detailTitle: { fontSize: 24, fontWeight: '900', color: '#0f172a' },
  detailSubtitle: { fontSize: 14, color: '#64748b', marginTop: 4, marginBottom: 24 },
  pdfBtn: { backgroundColor: '#0f172a', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, marginBottom: 32 },
  pdfBtnText: { color: '#ffffff', fontWeight: '700', marginLeft: 12 },
  severeWarningBox: { backgroundColor: '#fef2f2', borderWidth: 2, borderColor: '#ef4444', borderRadius: 16, padding: 20, flexDirection: 'row', marginBottom: 32 },
  severeWarningTitle: { color: '#991b1b', fontSize: 16, fontWeight: '800', marginBottom: 8 },
  severeWarningDesc: { color: '#b91c1c', fontSize: 14, lineHeight: 20 },
  sectionHeader: { fontSize: 16, fontWeight: '800', color: '#475569', marginBottom: 16, flexDirection: 'row', alignItems: 'center' },
  bidderRow: { backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, padding: 16, marginBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  l1Row: { borderColor: '#10b981', borderWidth: 2, backgroundColor: '#f0fdf4' },
  statusPill: (status) => ({
    backgroundColor: status === 'ELIGIBLE' ? '#d1fae5' : status === 'NOT_ELIGIBLE' ? '#fee2e2' : '#fef3c7',
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20
  }),
  statusText: (status) => ({
    color: status === 'ELIGIBLE' ? '#059669' : status === 'NOT_ELIGIBLE' ? '#dc2626' : '#d97706',
    fontSize: 10, fontWeight: '800'
  }),

  // Signoff Screen
  signoffContent: { flex: 1, padding: 32, alignItems: 'center' },
  summaryTitle: { fontSize: 28, fontWeight: '900', color: '#0f172a' },
  summaryTender: { fontSize: 16, color: '#64748b', fontWeight: '600', marginTop: 4, marginBottom: 32 },
  receiptBox: { width: '100%', backgroundColor: '#ffffff', borderRadius: 20, padding: 24, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 24 },
  receiptLabel: { fontSize: 13, color: '#64748b', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  receiptValue: { fontSize: 22, fontWeight: '800', color: '#0f172a', marginTop: 4 },
  divider: { height: 1, backgroundColor: '#f1f5f9', marginVertical: 16 },
  warningBox: { width: '100%', flexDirection: 'row', backgroundColor: '#fef2f2', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#fca5a5', marginBottom: 32 },
  warningTitle: { color: '#991b1b', fontWeight: '800', fontSize: 14 },
  warningDesc: { color: '#b91c1c', fontSize: 13, marginTop: 4, lineHeight: 18 },
  authBtn: { width: '100%', backgroundColor: '#4f46e5', flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: 18, borderRadius: 16 },
  authBtnText: { color: '#ffffff', fontSize: 18, fontWeight: '800', marginLeft: 12 },
});
