import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, SafeAreaView, Alert, Platform } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as LocalAuthentication from 'expo-local-authentication';
import { ShieldCheck, ArrowRight, AlertTriangle, Scale, CheckCircle2, FileText, ChevronRight, Fingerprint, LogOut } from 'lucide-react-native';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('login');
  const [selectedTender, setSelectedTender] = useState(null);

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
          
          <TouchableOpacity 
            style={styles.loginBtn}
            onPress={() => setCurrentScreen('dashboard')}
          >
            <Text style={styles.loginBtnText}>Secure Login (Gov ID)</Text>
            <ArrowRight color="#4F46E5" size={20} />
          </TouchableOpacity>
        </View>
        <Text style={styles.footerText}>Gov. of India • NIC Secured</Text>
      </View>
    );
  }

  if (currentScreen === 'dashboard') {
    return (
      <SafeAreaView style={styles.appContainer}>
        <StatusBar style="dark" />
        
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome, Joint Secretary</Text>
            <Text style={styles.subGreeting}>3 Tenders Awaiting Approval</Text>
          </View>
          <TouchableOpacity onPress={() => setCurrentScreen('login')} style={styles.logoutBtn}>
            <LogOut color="#64748b" size={20} />
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.scrollArea}>
          
          {/* Mock Tender 1 (Has Cartel Alert) */}
          <TouchableOpacity 
            style={[styles.card, styles.alertCardBorder]}
            onPress={() => {
              setSelectedTender({ id: 'TND-8A92B', l1: 'Alpha Corp', bid: '5,00,000', alert: true });
              setCurrentScreen('signoff');
            }}
          >
            <View style={styles.cardHeader}>
              <Text style={styles.tenderId}>TND-8A92B (IT Hardware)</Text>
              <View style={styles.alertBadge}>
                <AlertTriangle color="#dc2626" size={12} />
                <Text style={styles.alertText}>CARTEL RISK</Text>
              </View>
            </View>
            <Text style={styles.l1Text}>L1 Bidder: <Text style={styles.bold}>Alpha Corp</Text></Text>
            <Text style={styles.bidAmount}>Rs. 5,00,000</Text>
            
            <View style={styles.cardFooter}>
              <Text style={styles.footerActionText}>Review Exceptions</Text>
              <ChevronRight color="#4f46e5" size={16} />
            </View>
          </TouchableOpacity>

          {/* Mock Tender 2 (Clean) */}
          <TouchableOpacity 
            style={styles.card}
            onPress={() => {
              setSelectedTender({ id: 'TND-9B11C', l1: 'TechSolutions Ltd', bid: '12,40,000', alert: false });
              setCurrentScreen('signoff');
            }}
          >
            <View style={styles.cardHeader}>
              <Text style={styles.tenderId}>TND-9B11C (Cloud Services)</Text>
              <View style={styles.cleanBadge}>
                <CheckCircle2 color="#059669" size={12} />
                <Text style={styles.cleanText}>CLEAN</Text>
              </View>
            </View>
            <Text style={styles.l1Text}>L1 Bidder: <Text style={styles.bold}>TechSolutions Ltd</Text></Text>
            <Text style={styles.bidAmount}>Rs. 12,40,000</Text>
            
            <View style={styles.cardFooter}>
              <Text style={styles.footerActionText}>Ready for Sign-off</Text>
              <ChevronRight color="#4f46e5" size={16} />
            </View>
          </TouchableOpacity>

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
        // Fallback if simulator has no faceid
        Alert.alert("Success", "Tender Approved (Simulator Fallback).", [
          { text: "OK", onPress: () => setCurrentScreen('dashboard') }
        ]);
      }
    };

    return (
      <SafeAreaView style={styles.appContainer}>
        <StatusBar style="dark" />
        
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setCurrentScreen('dashboard')} style={{flexDirection: 'row', alignItems: 'center'}}>
            <ChevronRight color="#4f46e5" size={24} style={{transform: [{rotate: '180deg'}]}} />
            <Text style={{color: '#4f46e5', fontWeight: '600', fontSize: 16}}>Back</Text>
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
                <Text style={styles.warningDesc}>Junior officer noted that Alpha Corp and Beta Tech share a director, but authorized an override due to specialized vendor requirement.</Text>
              </View>
            </View>
          )}

          <TouchableOpacity style={styles.authBtn} onPress={handleAuthorize}>
            <Fingerprint color="#ffffff" size={24} />
            <Text style={styles.authBtnText}>Seal & Authorize</Text>
          </TouchableOpacity>
          <Text style={{textAlign: 'center', color: '#94a3b8', fontSize: 12, marginTop: 16}}>
            This action generates an immutable PDF audit trail.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  // Login
  loginContainer: {
    flex: 1,
    backgroundColor: '#312e81', // indigo-900 base
    justifyContent: 'center',
    alignItems: 'center',
  },
  loginContent: {
    alignItems: 'center',
    width: '100%',
    paddingHorizontal: 40,
  },
  iconWrapper: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    padding: 20,
    borderRadius: 30,
    marginBottom: 24,
  },
  loginTitle: {
    fontSize: 42,
    fontWeight: '900',
    color: '#ffffff',
    marginBottom: 8,
  },
  loginSubtitle: {
    fontSize: 16,
    color: '#a5b4fc', // indigo-300
    marginBottom: 48,
  },
  loginBtn: {
    backgroundColor: '#ffffff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 16,
    width: '100%',
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 10,
    elevation: 5,
  },
  loginBtnText: {
    color: '#4f46e5',
    fontSize: 18,
    fontWeight: '700',
    marginRight: 8,
  },
  footerText: {
    position: 'absolute',
    bottom: 40,
    color: '#818cf8',
    fontSize: 12,
  },

  // App Layout
  appContainer: {
    flex: 1,
    backgroundColor: '#f8fafc', // slate-50
  },
  header: {
    paddingHorizontal: 24,
    paddingTop: Platform.OS === 'android' ? 40 : 20,
    paddingBottom: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  greeting: {
    fontSize: 20,
    fontWeight: '800',
    color: '#0f172a', // slate-900
  },
  subGreeting: {
    fontSize: 14,
    color: '#64748b', // slate-500
    marginTop: 4,
  },
  logoutBtn: {
    padding: 8,
    backgroundColor: '#f1f5f9',
    borderRadius: 12,
  },
  scrollArea: {
    padding: 24,
  },

  // Cards
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0', // slate-200
    shadowColor: '#64748b',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 10,
    elevation: 2,
  },
  alertCardBorder: {
    borderLeftWidth: 4,
    borderLeftColor: '#dc2626',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  tenderId: {
    fontSize: 14,
    fontWeight: '700',
    color: '#475569',
  },
  alertBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fef2f2',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#fee2e2',
  },
  alertText: {
    color: '#dc2626',
    fontSize: 10,
    fontWeight: '800',
    marginLeft: 4,
  },
  cleanBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ecfdf5',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d1fae5',
  },
  cleanText: {
    color: '#059669',
    fontSize: 10,
    fontWeight: '800',
    marginLeft: 4,
  },
  l1Text: {
    fontSize: 16,
    color: '#334155',
  },
  bold: {
    fontWeight: '800',
    color: '#0f172a',
  },
  bidAmount: {
    fontSize: 24,
    fontWeight: '900',
    color: '#10b981', // emerald-500
    marginTop: 8,
    marginBottom: 20,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
    paddingTop: 16,
  },
  footerActionText: {
    color: '#4f46e5',
    fontWeight: '700',
    fontSize: 14,
  },

  // Signoff Screen
  signoffContent: {
    flex: 1,
    padding: 32,
    alignItems: 'center',
  },
  summaryTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: '#0f172a',
  },
  summaryTender: {
    fontSize: 16,
    color: '#64748b',
    fontWeight: '600',
    marginTop: 4,
    marginBottom: 32,
  },
  receiptBox: {
    width: '100%',
    backgroundColor: '#ffffff',
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 24,
  },
  receiptLabel: {
    fontSize: 13,
    color: '#64748b',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  receiptValue: {
    fontSize: 22,
    fontWeight: '800',
    color: '#0f172a',
    marginTop: 4,
  },
  divider: {
    height: 1,
    backgroundColor: '#f1f5f9',
    marginVertical: 16,
  },
  warningBox: {
    width: '100%',
    flexDirection: 'row',
    backgroundColor: '#fef2f2',
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#fca5a5',
    marginBottom: 32,
  },
  warningTitle: {
    color: '#991b1b',
    fontWeight: '800',
    fontSize: 14,
  },
  warningDesc: {
    color: '#b91c1c',
    fontSize: 13,
    marginTop: 4,
    lineHeight: 18,
  },
  authBtn: {
    width: '100%',
    backgroundColor: '#4f46e5',
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 18,
    borderRadius: 16,
    shadowColor: '#4f46e5',
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 8 },
    shadowRadius: 15,
    elevation: 8,
  },
  authBtnText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '800',
    marginLeft: 12,
  },
});
