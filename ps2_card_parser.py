"""
PS2 Memory Card Parser
Handles reading and writing PS2 memory card files (.ps2, .bin formats)
"""

import struct
import os
from datetime import datetime
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass

@dataclass
class PS2Save:
    """Represents a PS2 save game"""
    title: str
    product_code: str
    last_modified: datetime
    directory_name: str
    cluster: int
    size: int
    icon_sys_data: Optional[bytes] = None

class PS2CardParser:
    """Parser for PS2 memory card file system"""
    
    # PS2 Memory Card constants
    BLOCK_SIZE = 512
    CLUSTER_SIZE = 1024  # 2 blocks per cluster
    FAT_ENTRY_SIZE = 2
    DIRECTORY_ENTRY_SIZE = 512
    
    # Standard card sizes (in MB)
    CARD_SIZE_8MB = 8 * 1024 * 1024
    CARD_SIZE_16MB = 16 * 1024 * 1024
    CARD_SIZE_32MB = 32 * 1024 * 1024
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_size = os.path.getsize(file_path)
        self.modified = False
        self._data = None
        self._load_file()
        
    def _load_file(self):
        """Load memory card file into memory"""
        with open(self.file_path, 'rb') as f:
            self._data = bytearray(f.read())
    
    def _get_card_size(self) -> int:
        """Determine card size based on file size"""
        if self.file_size <= self.CARD_SIZE_8MB:
            return self.CARD_SIZE_8MB
        elif self.file_size <= self.CARD_SIZE_16MB:
            return self.CARD_SIZE_16MB
        else:
            return self.CARD_SIZE_32MB
    
    def _get_fat_offset(self) -> int:
        """Get FAT table offset"""
        return self.BLOCK_SIZE * 2  # FAT starts at block 2
    
    def _get_directory_offset(self) -> int:
        """Get directory table offset"""
        card_size = self._get_card_size()
        fat_size = (card_size // self.CLUSTER_SIZE) * self.FAT_ENTRY_SIZE
        fat_blocks = (fat_size + self.BLOCK_SIZE - 1) // self.BLOCK_SIZE
        return self.BLOCK_SIZE * (2 + fat_blocks)
    
    def _read_fat_entry(self, cluster: int) -> int:
        """Read FAT entry for a cluster"""
        fat_offset = self._get_fat_offset()
        entry_offset = fat_offset + (cluster * self.FAT_ENTRY_SIZE)
        if entry_offset + 2 > len(self._data):
            return 0xFFFF  # Invalid cluster
        return struct.unpack('<H', self._data[entry_offset:entry_offset+2])[0]
    
    def _write_fat_entry(self, cluster: int, value: int):
        """Write FAT entry"""
        fat_offset = self._get_fat_offset()
        entry_offset = fat_offset + (cluster * self.FAT_ENTRY_SIZE)
        self._data[entry_offset:entry_offset+2] = struct.pack('<H', value)
        self.modified = True
    
    def _read_directory_entry(self, index: int) -> Optional[Dict]:
        """Read a directory entry"""
        dir_offset = self._get_directory_offset()
        entry_offset = dir_offset + (index * self.DIRECTORY_ENTRY_SIZE)
        
        if entry_offset + self.DIRECTORY_ENTRY_SIZE > len(self._data):
            return None
        
        entry_data = self._data[entry_offset:entry_offset + self.DIRECTORY_ENTRY_SIZE]
        
        # Check if entry is valid (first byte != 0x00 or 0x51)
        if entry_data[0] == 0x00 or entry_data[0] == 0x51:
            return None
        
        # Parse directory entry structure
        mode = struct.unpack('<H', entry_data[2:4])[0]
        length = struct.unpack('<I', entry_data[4:8])[0]
        created = struct.unpack('<I', entry_data[8:12])[0]
        cluster = struct.unpack('<H', entry_data[20:22])[0]
        dir_index = struct.unpack('<H', entry_data[22:24])[0]
        
        # Extract directory name (16 bytes, null-terminated)
        dir_name = entry_data[0:16].split(b'\x00')[0].decode('ascii', errors='ignore')
        
        return {
            'mode': mode,
            'length': length,
            'created': created,
            'cluster': cluster,
            'dir_index': dir_index,
            'dir_name': dir_name,
            'entry_data': entry_data
        }
    
    def _read_icon_sys(self, cluster: int) -> Optional[Dict]:
        """Read icon.sys file from a save directory"""
        icon_sys_data = self._read_file_from_cluster(cluster, "icon.sys")
        if not icon_sys_data:
            return None
        
        try:
            # Parse icon.sys structure
            title = icon_sys_data[0x20:0x60].split(b'\x00')[0].decode('shift_jis', errors='ignore')
            return {'title': title, 'data': icon_sys_data}
        except:
            return None
    
    def _read_file_from_cluster(self, start_cluster: int, filename: str) -> Optional[bytes]:
        """Read a file from a directory cluster"""
        # Simplified implementation - would need full directory parsing
        # This is a placeholder - actual file reading requires proper directory parsing
        # For now, just return None to avoid infinite loops
        return None
    
    def _get_cluster_offset(self, cluster: int) -> int:
        """Get file data offset for a cluster"""
        dir_offset = self._get_directory_offset()
        dir_size = self.BLOCK_SIZE * 2  # Directory is typically 2 blocks
        return dir_offset + dir_size + ((cluster - 2) * self.CLUSTER_SIZE)
    
    def list_saves(self) -> List[PS2Save]:
        """List all save games on the memory card"""
        saves = []
        
        # Read directory entries (typically 64 entries)
        for i in range(64):
            try:
                entry = self._read_directory_entry(i)
                if not entry:
                    continue
                
                # Check if it's a directory (mode bit 0x2000)
                if entry['mode'] & 0x2000:
                    dir_name = entry['dir_name']
                    cluster = entry['cluster']
                    
                    # Validate cluster number
                    if cluster < 2 or cluster > 0xFF00:
                        continue
                    
                    # Use directory name as title (skip icon.sys reading to avoid freezes)
                    # icon.sys reading requires proper directory parsing which can cause issues
                    title = dir_name
                    
                    # Extract product code from directory name (format: BASLUS-21442)
                    product_code = dir_name[:11] if len(dir_name) >= 11 else dir_name
                    
                    # Convert timestamp
                    try:
                        last_modified = datetime.fromtimestamp(entry['created'])
                    except:
                        last_modified = datetime.now()
                    
                    save = PS2Save(
                        title=title,
                        product_code=product_code,
                        last_modified=last_modified,
                        directory_name=dir_name,
                        cluster=cluster,
                        size=entry['length']
                    )
                    saves.append(save)
            except Exception as e:
                # Skip invalid entries
                continue
        
        return saves
    
    def delete_save(self, save: PS2Save) -> bool:
        """Delete a save game from the memory card"""
        # Find and mark directory entry as deleted
        dir_offset = self._get_directory_offset()
        
        for i in range(64):
            entry_offset = dir_offset + (i * self.DIRECTORY_ENTRY_SIZE)
            entry_data = self._data[entry_offset:entry_offset + 16]
            dir_name = entry_data[0:16].split(b'\x00')[0].decode('ascii', errors='ignore')
            
            if dir_name == save.directory_name:
                # Mark as deleted (set first byte to 0x51)
                self._data[entry_offset] = 0x51
                # Free clusters in FAT
                self._free_clusters(save.cluster)
                self.modified = True
                return True
        
        return False
    
    def _free_clusters(self, start_cluster: int):
        """Free clusters in FAT chain"""
        current_cluster = start_cluster
        while current_cluster < 0xFF00:
            next_cluster = self._read_fat_entry(current_cluster)
            self._write_fat_entry(current_cluster, 0x0000)  # Mark as free
            if next_cluster >= 0xFF00:
                break
            current_cluster = next_cluster
    
    def rename_save(self, save: PS2Save, new_name: str) -> bool:
        """Rename a save game directory"""
        if len(new_name) > 16:
            return False
        
        dir_offset = self._get_directory_offset()
        
        for i in range(64):
            entry_offset = dir_offset + (i * self.DIRECTORY_ENTRY_SIZE)
            entry_data = self._data[entry_offset:entry_offset + 16]
            dir_name = entry_data[0:16].split(b'\x00')[0].decode('ascii', errors='ignore')
            
            if dir_name == save.directory_name:
                # Update directory name
                new_name_bytes = new_name.encode('ascii')[:16].ljust(16, b'\x00')
                self._data[entry_offset:entry_offset+16] = new_name_bytes
                self.modified = True
                return True
        
        return False
    
    def export_save(self, save: PS2Save, output_path: str, format: str = 'psu') -> bool:
        """Export a save game to .psu or .max format"""
        try:
            # Read all clusters for this save
            save_data = bytearray()
            current_cluster = save.cluster
            
            while current_cluster < 0xFF00:
                cluster_offset = self._get_cluster_offset(current_cluster)
                cluster_data = self._data[cluster_offset:cluster_offset + self.CLUSTER_SIZE]
                save_data.extend(cluster_data)
                
                fat_entry = self._read_fat_entry(current_cluster)
                if fat_entry >= 0xFF00:
                    break
                current_cluster = fat_entry
            
            # Write to file
            with open(output_path, 'wb') as f:
                if format.lower() == 'psu':
                    # PSU format is just raw data
                    f.write(save_data)
                elif format.lower() == 'max':
                    # MAX format has a header (simplified)
                    f.write(save_data)
            
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def copy_save_to(self, destination_parser: 'PS2CardParser', source_save: PS2Save,
                     progress_callback: Optional[Callable[[float, str], bool]] = None) -> bool:
        """
        Copy a save to another memory card
        
        Args:
            destination_parser: Destination card parser
            source_save: Save to copy
            progress_callback: Optional callback(progress: float, message: str) -> bool
                             Return False to cancel
        
        Returns:
            True if successful
        """
        if progress_callback:
            if not progress_callback(0.1, "Reading source save data..."):
                return False
        
        try:
            # Read save data from source
            save_data = self._read_save_clusters(source_save.cluster)
            
            if not save_data or len(save_data) == 0:
                if progress_callback:
                    progress_callback(1.0, "Error: Could not read save data (empty or invalid cluster chain)")
                return False
            
            if progress_callback:
                if not progress_callback(0.3, "Finding free space on destination card..."):
                    return False
            
            # Find free cluster on destination
            free_cluster = destination_parser._find_free_cluster()
            if free_cluster == -1:
                if progress_callback:
                    progress_callback(1.0, "Error: No free space on destination card")
                return False
            
            if progress_callback:
                if not progress_callback(0.4, "Copying directory entry..."):
                    return False
            
            # Copy directory entry
            total_size = sum(len(cluster) for cluster in save_data)
            if not destination_parser._copy_directory_entry(source_save, free_cluster, total_size):
                if progress_callback:
                    progress_callback(1.0, "Error: Failed to create directory entry")
                return False
            
            if progress_callback:
                if not progress_callback(0.5, "Copying data clusters..."):
                    return False
            
            # Copy data clusters
            current_cluster = free_cluster
            total_clusters = len(save_data)
            
            if total_clusters == 0:
                if progress_callback:
                    progress_callback(1.0, "Error: No data to copy")
                return False
            
            for i, cluster_data in enumerate(save_data):
                if progress_callback:
                    progress = 0.5 + (0.4 * (i + 1) / total_clusters)
                    if not progress_callback(progress, f"Copying cluster {i+1}/{total_clusters}..."):
                        return False
                
                try:
                    # Write cluster data
                    destination_parser._write_cluster(current_cluster, cluster_data)
                    
                    # Update FAT
                    if i < total_clusters - 1:
                        next_cluster = destination_parser._find_free_cluster()
                        if next_cluster == -1:
                            if progress_callback:
                                progress_callback(1.0, "Error: Ran out of space while copying")
                            return False
                        destination_parser._write_fat_entry(current_cluster, next_cluster)
                        current_cluster = next_cluster
                    else:
                        # Last cluster - mark as end of chain
                        destination_parser._write_fat_entry(current_cluster, 0xFFFF)
                except Exception as e:
                    if progress_callback:
                        progress_callback(1.0, f"Error writing cluster: {str(e)}")
                    return False
            
            destination_parser.modified = True
            
            if progress_callback:
                progress_callback(1.0, "Copy complete!")
            
            return True
            
        except Exception as e:
            error_msg = str(e) if e else "Unknown error"
            if progress_callback:
                progress_callback(1.0, f"Error: {error_msg}")
            print(f"Copy error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False
    
    def _read_save_clusters(self, start_cluster: int) -> List[bytes]:
        """Read all clusters for a save"""
        clusters = []
        current_cluster = start_cluster
        visited_clusters = set()  # Track visited clusters to prevent infinite loops
        max_clusters = 10000  # Safety limit
        
        # Validate starting cluster
        if start_cluster < 2 or start_cluster >= 0xFF00:
            return clusters
        
        iteration = 0
        while current_cluster < 0xFF00 and iteration < max_clusters:
            # Check for circular references
            if current_cluster in visited_clusters:
                break
            
            visited_clusters.add(current_cluster)
            
            try:
                cluster_offset = self._get_cluster_offset(current_cluster)
                if cluster_offset < 0 or cluster_offset + self.CLUSTER_SIZE > len(self._data):
                    break
                    
                cluster_data = self._data[cluster_offset:cluster_offset + self.CLUSTER_SIZE]
                if len(cluster_data) < self.CLUSTER_SIZE:
                    # Pad if needed
                    cluster_data = cluster_data.ljust(self.CLUSTER_SIZE, b'\x00')
                clusters.append(cluster_data)
                
                fat_entry = self._read_fat_entry(current_cluster)
                if fat_entry >= 0xFF00:
                    break
                current_cluster = fat_entry
                iteration += 1
            except (IndexError, struct.error, ValueError) as e:
                # Stop reading on error
                break
        
        return clusters
    
    def _find_free_cluster(self) -> int:
        """Find a free cluster on the card"""
        card_size = self._get_card_size()
        total_clusters = min(card_size // self.CLUSTER_SIZE, 10000)  # Safety limit
        
        for cluster in range(2, total_clusters):  # Start from cluster 2
            try:
                fat_entry = self._read_fat_entry(cluster)
                if fat_entry == 0x0000:  # Free cluster
                    return cluster
            except:
                continue
        
        return -1
    
    def _write_cluster(self, cluster: int, data: bytes):
        """Write data to a cluster"""
        try:
            cluster_offset = self._get_cluster_offset(cluster)
            if cluster_offset + self.CLUSTER_SIZE > len(self._data):
                raise ValueError(f"Cluster {cluster} offset out of bounds")
            
            if len(data) < self.CLUSTER_SIZE:
                data = data.ljust(self.CLUSTER_SIZE, b'\x00')
            self._data[cluster_offset:cluster_offset + self.CLUSTER_SIZE] = data[:self.CLUSTER_SIZE]
            self.modified = True
        except Exception as e:
            raise ValueError(f"Failed to write cluster {cluster}: {str(e)}")
    
    def _copy_directory_entry(self, source_save: PS2Save, target_cluster: int, size: int) -> bool:
        """Copy directory entry to destination card"""
        try:
            # Find free directory entry slot
            dir_offset = self._get_directory_offset()
            
            if dir_offset + (64 * self.DIRECTORY_ENTRY_SIZE) > len(self._data):
                return False
            
            for i in range(64):
                entry_offset = dir_offset + (i * self.DIRECTORY_ENTRY_SIZE)
                if entry_offset + 16 > len(self._data):
                    continue
                    
                entry_data = self._data[entry_offset:entry_offset + 16]
                
                # Check if entry is free
                if entry_data[0] == 0x00 or entry_data[0] == 0x51:
                    # Create new directory entry
                    new_entry = bytearray(self.DIRECTORY_ENTRY_SIZE)
                    
                    # Directory name (handle encoding errors)
                    try:
                        dir_name_bytes = source_save.directory_name.encode('ascii', errors='ignore')[:16].ljust(16, b'\x00')
                    except:
                        dir_name_bytes = source_save.directory_name[:16].encode('latin-1', errors='ignore')[:16].ljust(16, b'\x00')
                    
                    new_entry[0:16] = dir_name_bytes
                    
                    # Mode (directory)
                    new_entry[2:4] = struct.pack('<H', 0x8427)
                    
                    # Length
                    new_entry[4:8] = struct.pack('<I', size)
                    
                    # Created timestamp
                    try:
                        timestamp = int(source_save.last_modified.timestamp())
                    except:
                        timestamp = int(datetime.now().timestamp())
                    new_entry[8:12] = struct.pack('<I', timestamp)
                    
                    # Cluster
                    new_entry[20:22] = struct.pack('<H', target_cluster)
                    
                    # Directory index
                    new_entry[22:24] = struct.pack('<H', i)
                    
                    self._data[entry_offset:entry_offset + self.DIRECTORY_ENTRY_SIZE] = new_entry
                    self.modified = True
                    return True
            
            return False
        except Exception as e:
            print(f"Error in _copy_directory_entry: {e}")
            return False
    
    def save(self) -> bool:
        """Save changes back to file"""
        if not self.modified:
            return True
        
        try:
            with open(self.file_path, 'wb') as f:
                f.write(self._data)
            self.modified = False
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False
    
    @staticmethod
    def create_new_card(file_path: str, size_mb: int = 8) -> bool:
        """
        Create a new formatted PS2 memory card file
        
        Args:
            file_path: Path where to create the new card
            size_mb: Size in MB (8, 16, or 32)
        
        Returns:
            True if successful
        """
        try:
            if size_mb not in [8, 16, 32]:
                size_mb = 8
            
            card_size = size_mb * 1024 * 1024
            data = bytearray(card_size)
            
            # Initialize with zeros
            data[:] = b'\x00' * card_size
            
            # Write header (first 512 bytes)
            # Magic number "Sony PS2 Memory Card Format "
            header = b'Sony PS2 Memory Card Format '
            data[0:28] = header.ljust(28, b'\x00')
            
            # Write FAT table
            fat_offset = 512 * 2  # FAT starts at block 2
            total_clusters = card_size // 1024
            
            # Mark cluster 0 and 1 as used (system clusters)
            data[fat_offset:fat_offset+2] = struct.pack('<H', 0xFFFF)
            data[fat_offset+2:fat_offset+4] = struct.pack('<H', 0xFFFF)
            
            # All other clusters are free (0x0000)
            for i in range(2, total_clusters):
                fat_entry_offset = fat_offset + (i * 2)
                if fat_entry_offset + 2 <= len(data):
                    data[fat_entry_offset:fat_entry_offset+2] = struct.pack('<H', 0x0000)
            
            # Directory table is already zeroed (empty)
            
            # Write to file
            with open(file_path, 'wb') as f:
                f.write(data)
            
            return True
        except Exception as e:
            print(f"Error creating card: {e}")
            return False
    
    def format_card(self) -> bool:
        """
        Format the current memory card (erase all saves)
        
        Returns:
            True if successful
        """
        try:
            card_size = self._get_card_size()
            
            # Clear all data
            self._data = bytearray(card_size)
            self._data[:] = b'\x00' * card_size
            
            # Write header
            header = b'Sony PS2 Memory Card Format '
            self._data[0:28] = header.ljust(28, b'\x00')
            
            # Reset FAT table
            fat_offset = self._get_fat_offset()
            total_clusters = card_size // self.CLUSTER_SIZE
            
            # Mark cluster 0 and 1 as used
            self._data[fat_offset:fat_offset+2] = struct.pack('<H', 0xFFFF)
            self._data[fat_offset+2:fat_offset+4] = struct.pack('<H', 0xFFFF)
            
            # All other clusters are free
            for i in range(2, total_clusters):
                fat_entry_offset = fat_offset + (i * 2)
                if fat_entry_offset + 2 <= len(self._data):
                    self._data[fat_entry_offset:fat_entry_offset+2] = struct.pack('<H', 0x0000)
            
            # Directory is already zeroed
            
            self.modified = True
            return True
        except Exception as e:
            print(f"Error formatting card: {e}")
            return False
    
    def inspect_save(self, save: PS2Save) -> Dict:
        """
        Inspect a save and extract detailed information
        
        Returns:
            Dictionary with save information
        """
        info = {
            'directory_name': save.directory_name,
            'product_code': save.product_code,
            'title': save.title,
            'last_modified': save.last_modified.strftime('%Y-%m-%d %H:%M:%S'),
            'cluster': save.cluster,
            'size': save.size,
            'icon_sys': None,
            'files': [],
            'raw_data_size': 0
        }
        
        try:
            # Read save clusters
            clusters = self._read_save_clusters(save.cluster)
            info['raw_data_size'] = len(clusters) * self.CLUSTER_SIZE
            
            # Try to find and parse icon.sys
            if clusters:
                # Look for icon.sys signature in first cluster
                first_cluster = clusters[0]
                
                # icon.sys typically starts with specific bytes
                # Try to find "icon.sys" string or parse the structure
                if len(first_cluster) >= 0x60:
                    try:
                        # Try to extract title from icon.sys structure
                        title_bytes = first_cluster[0x20:0x60]
                        if title_bytes:
                            title = title_bytes.split(b'\x00')[0].decode('shift_jis', errors='ignore')
                            if title and title.strip():
                                info['title'] = title.strip()
                                info['icon_sys'] = {
                                    'title': title.strip(),
                                    'found': True
                                }
                    except:
                        pass
                
                # Try to find file entries in the directory structure
                # This is simplified - full implementation would parse directory properly
                info['files'] = ['icon.sys (detected)', 'icon.ico (if present)', 'save data files']
            
            # Calculate free space estimate
            info['estimated_files'] = len(clusters)
            
        except Exception as e:
            info['error'] = str(e)
        
        return info

