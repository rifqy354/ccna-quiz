'use client';

import {createContext,useCallback,useContext,useEffect,useState,ReactNode} from 'react';
import {api,ApiError,Player} from './api';


interface PlayerContextValue {
  player: Player | null;
  loading: boolean;
  error: string | null;
  createPlayer(name: string): Promise<void>;
  refreshPlayer(): Promise<void>;
  clearPlayer(): void;
}


const PlayerContext=createContext<PlayerContextValue|null>(null);


export function PlayerProvider({children}:{children:ReactNode}){
  const [player,setPlayer]=useState<Player|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);

  const refreshPlayer=useCallback(async()=>{
    setLoading(true);
    setError(null);
    try {
      setPlayer(await api.player.me());
    } catch (caught) {
      setPlayer(null);
      if (!(caught instanceof ApiError && caught.status===401)) {
        setError(caught instanceof Error?caught.message:'Unable to load player');
      }
    } finally {
      setLoading(false);
    }
  },[]);

  useEffect(()=>{void refreshPlayer();},[refreshPlayer]);

  const createPlayer=useCallback(async(name:string)=>{
    setError(null);
    try {
      setPlayer(await api.player.create(name));
    } catch (caught) {
      setPlayer(null);
      setError(caught instanceof Error?caught.message:'Unable to create player');
    }
  },[]);

  const clearPlayer=useCallback(()=>{
    setPlayer(null);
    setError(null);
    setLoading(false);
  },[]);

  return <PlayerContext.Provider value={{
    player,loading,error,createPlayer,refreshPlayer,clearPlayer,
  }}>{children}</PlayerContext.Provider>;
}


export function usePlayer(){
  const context=useContext(PlayerContext);
  if(!context) throw new Error('usePlayer must be used within PlayerProvider');
  return context;
}
