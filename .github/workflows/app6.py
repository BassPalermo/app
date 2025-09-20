#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import requests
import json
import threading
from pathlib import Path
import time
from PIL import Image, ImageTk
import io

class AdvancedEdenAIGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Eden AI - Reconocimiento Facial Avanzado")
        self.root.geometry("1400x900")
        
        # Intentar maximizar de forma compatible
        try:
            self.root.state('zoomed')  # Windows
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)  # Linux alternativo
            except tk.TclError:
                # Si no funciona, usar tamaño grande
                self.root.geometry("1400x900")
                # Centrar ventana
                self.root.update_idletasks()
                x = (self.root.winfo_screenwidth() - 1400) // 2
                y = (self.root.winfo_screenheight() - 900) // 2
                self.root.geometry(f"1400x900+{x}+{y}")
        
        # Variables
        self.api_key = tk.StringVar(value="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMWFmZmYzNzEtZjAxOS00MzAyLTgyMTctODZmOTYxM2IyYjAwIiwidHlwZSI6ImFwaV90b2tlbiJ9.aTxgNluJ6eO9LtWfiRpXo13xhTw7bE5bL6HnCd8koPY")
        self.current_folder = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Sistema listo - Selecciona carpeta e imágenes")
        
        # Almacenamiento de imágenes y resultados
        self.image_files = []
        self.selected_images = set()
        self.thumbnails_cache = {}
        self.results_cache = {}
        self.detected_faces = []  # Nueva lista para caras detectadas
        self.face_identifications = {}  # Base de datos de identificaciones {face_id: name}
        
        # Configurar estilo
        self.setup_style()
        self.create_widgets()
        
    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores personalizados
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        
        # Estilo personalizado para el árbol de carpetas
        style.configure("Custom.Treeview", 
                       font=('Arial', 10),
                       rowheight=28,  # Altura de cada fila
                       fieldbackground='white',
                       background='white')
        style.configure("Custom.Treeview.Heading", 
                       font=('Arial', 10, 'bold'))
        
        # Estilo para la tabla de resultados también
        style.configure("Results.Treeview",
                       font=('Arial', 9),
                       rowheight=24)
        style.configure("Results.Treeview.Heading",
                       font=('Arial', 9, 'bold'))
        
    def create_widgets(self):
        # Frame principal con paneles
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panel izquierdo: Explorador y configuración
        left_frame = ttk.Frame(main_paned, width=350)
        main_paned.add(left_frame, weight=0)
        
        # Panel derecho: Miniaturas y resultados
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)
        
        self.create_left_panel(left_frame)
        self.create_right_panels(right_paned)
        
    def create_left_panel(self, parent):
        # Configuración de API
        config_frame = ttk.LabelFrame(parent, text="Configuración", padding="10")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(config_frame, text="API Key Eden AI:", style='Header.TLabel').pack(anchor=tk.W)
        api_entry = ttk.Entry(config_frame, textvariable=self.api_key, width=40, show="*", state="readonly")
        api_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Estado de API (siempre válida ahora)
        self.api_status_label = ttk.Label(config_frame, text="API Key configurada", style='Success.TLabel')
        self.api_status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Explorador de carpetas
        explorer_frame = ttk.LabelFrame(parent, text="Explorador de Carpetas", padding="10")
        explorer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Botones de navegación
        nav_frame = ttk.Frame(explorer_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(nav_frame, text="🏠", width=3, command=self.go_home).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(nav_frame, text="⬆", width=3, command=self.go_up).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(nav_frame, text="🔄", width=3, command=self.refresh_folder).pack(side=tk.LEFT, padx=(0, 2))
        
        # Ruta actual
        path_frame = ttk.Frame(explorer_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(path_frame, text="Ruta:").pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.current_folder, width=30)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.path_entry.bind('<Return>', lambda e: self.load_folder(self.current_folder.get()))
        
        # Árbol de carpetas
        tree_frame = ttk.Frame(explorer_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.folder_tree = ttk.Treeview(tree_frame, height=15, style="Custom.Treeview")
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.folder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Eventos del árbol
        self.folder_tree.bind('<<TreeviewSelect>>', self.on_folder_select)
        self.folder_tree.bind('<Double-Button-1>', self.on_folder_double_click)
        
        # Controles de procesamiento
        control_frame = ttk.LabelFrame(parent, text="Control de Procesamiento", padding="10")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Botones de selección
        selection_frame = ttk.Frame(control_frame)
        selection_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(selection_frame, text="Seleccionar Todo", command=self.select_all_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_frame, text="Deseleccionar", command=self.clear_selection).pack(side=tk.LEFT)
        
        # Información de selección
        self.selection_info = ttk.Label(control_frame, text="0 imágenes seleccionadas")
        self.selection_info.pack(anchor=tk.W, pady=(0, 5))
        
        # Opciones de procesamiento
        self.save_results = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Guardar resultados JSON", variable=self.save_results).pack(anchor=tk.W)
        
        self.auto_open_results = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Abrir resultados automáticamente", variable=self.auto_open_results).pack(anchor=tk.W)
        
        # Botones de procesamiento
        self.detect_btn = ttk.Button(control_frame, text="Detectar Rostros", 
                                    command=self.start_face_detection, style='Title.TLabel')
        self.detect_btn.pack(fill=tk.X, pady=(10, 5))
        
        self.add_faces_btn = ttk.Button(control_frame, text="Agregar Caras a Lista", 
                                       command=self.add_faces_to_list, state='disabled')
        self.add_faces_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Barra de progreso
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(progress_frame, text="Progreso:").pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Estado
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, wraplength=300)
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Inicializar explorador
        self.initialize_explorer()
        
    def create_right_panels(self, parent):
        # Panel superior: Vista de miniaturas
        thumbnails_frame = ttk.LabelFrame(parent, text="Vista de Imágenes", padding="10")
        parent.add(thumbnails_frame, weight=2)
        
        # Marco con scroll para miniaturas
        canvas_frame = ttk.Frame(thumbnails_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        canvas_scrollbar_v = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        canvas_scrollbar_h = ttk.Scrollbar(thumbnails_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=canvas_scrollbar_v.set, xscrollcommand=canvas_scrollbar_h.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Frame interno para las miniaturas
        self.thumbnails_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.thumbnails_frame, anchor='nw')
        
        # Eventos del canvas
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        # Scroll compatible con Linux
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)  # Windows/macOS
        self.canvas.bind('<Button-4>', self.on_mousewheel)    # Linux scroll up
        self.canvas.bind('<Button-5>', self.on_mousewheel)    # Linux scroll down
        
        # Panel inferior: Resultados detallados
        results_frame = ttk.LabelFrame(parent, text="Resultados Detallados", padding="10")
        parent.add(results_frame, weight=1)
        
        # Pestañas para resultados
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de resumen
        summary_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(summary_frame, text="Resumen")
        
        self.summary_text = tk.Text(summary_frame, height=8, font=('Consolas', 10))
        summary_scroll = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Pestaña de detalles
        details_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(details_frame, text="Detalles")
        
        columns = ('Archivo', 'Rostros', 'Confianza', 'Estado', 'Tamaño')
        self.details_tree = ttk.Treeview(details_frame, columns=columns, show='tree headings', 
                                        height=10, style="Results.Treeview")
        
        for col in ['#0'] + list(columns):
            if col == '#0':
                self.details_tree.heading(col, text='#')
                self.details_tree.column(col, width=30)
            else:
                self.details_tree.heading(col, text=col)
                self.details_tree.column(col, width=100)
        
        details_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_tree.yview)
        self.details_tree.configure(yscrollcommand=details_scroll.set)
        
        self.details_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def update_selection_info(self):
        total = len(self.image_files)
        selected = len(self.selected_images)
        faces = len(self.detected_faces)
        identified = len(self.face_identifications)
        self.selection_info.config(text=f"{selected}/{total} imágenes | {faces} caras detectadas | {identified} identificadas")
        
    def start_face_detection(self):
        """Iniciar detección de rostros en imágenes seleccionadas"""
        if not self.selected_images:
            messagebox.showerror("Error", "Por favor selecciona al menos una imagen")
            return
            
        self.detect_btn.config(state='disabled')
        self.add_faces_btn.config(state='disabled')
        self.detected_faces.clear()
        
        # Limpiar resultados anteriores
        for item in self.details_tree.get_children():
            self.details_tree.delete(item)
        self.summary_text.delete(1.0, tk.END)
        
        threading.Thread(target=self.detect_faces_process, daemon=True).start()
        
    def detect_faces_process(self):
        """Proceso de detección de rostros"""
        try:
            selected_paths = [Path(path) for path in self.selected_images]
            total_images = len(selected_paths)
            
            self.status_var.set(f"Detectando rostros en {total_images} imágenes...")
            
            successful = 0
            total_faces = 0
            
            for i, image_path in enumerate(selected_paths):
                self.status_var.set(f"Analizando {i+1}/{total_images}: {image_path.name}")
                
                progress = (i / total_images) * 100
                self.progress_var.set(progress)
                
                # Procesar imagen
                result = self.process_single_image(str(image_path))
                self.results_cache[str(image_path)] = result
                
                # Extraer caras detectadas
                faces_count = 0
                confidence = "N/A"
                status = "Error"
                
                if 'error' not in result and 'amazon' in result:
                    items = result.get('amazon', {}).get('items', [])
                    faces_count = len(items)
                    status = "Exitoso"
                    successful += 1
                    total_faces += faces_count
                    
                    # Agregar cada cara detectada a la lista
                    for face_data in items:
                        face_info = {
                            'image_path': str(image_path),
                            'image_name': image_path.name,
                            'confidence': face_data.get('confidence', 0),
                            'bounding_box': face_data.get('bounding_box', {}),
                            'landmarks': face_data.get('landmarks', {}),
                            'attributes': face_data.get('attributes', {}),
                            'face_id': f"{image_path.name}_{len(self.detected_faces)}"  # ID único para cada cara
                        }
                        self.detected_faces.append(face_info)
                    
                    if items:
                        confidence = f"{items[0].get('confidence', 0):.2f}"
                
                # Actualizar tabla en hilo principal
                size_mb = round(image_path.stat().st_size / (1024*1024), 2)
                self.root.after(0, self.add_result_to_table, i+1, image_path.name, 
                              faces_count, confidence, status, f"{size_mb} MB")
                
                time.sleep(0.3)  # Pausa más corta
                
            # Completar detección
            self.progress_var.set(100)
            self.status_var.set(f"Detección completa: {total_faces} rostros encontrados en {total_images} imágenes")
            
            # Habilitar botón de agregar si hay caras detectadas
            if self.detected_faces:
                self.root.after(0, lambda: self.add_faces_btn.config(state='normal'))
            
            # Actualizar información
            self.root.after(0, self.update_selection_info)
            
            # Generar resumen
            summary = self.generate_detection_summary(total_images, successful, total_faces)
            self.root.after(0, lambda: self.summary_text.insert(tk.END, summary))
            
            # Guardar resultados
            if self.save_results.get():
                self.save_results_to_file()
                
        except Exception as e:
            self.status_var.set(f"Error en detección: {str(e)}")
        finally:
            self.root.after(0, lambda: self.detect_btn.config(state='normal'))
            
    def add_faces_to_list(self):
        """Agregar caras detectadas a una lista de gestión"""
        if not self.detected_faces:
            messagebox.showwarning("Sin datos", "No hay caras detectadas para agregar")
            return
            
        # Crear ventana para mostrar las caras detectadas
        faces_window = tk.Toplevel(self.root)
        faces_window.title("Caras Detectadas - Lista de Gestión")
        faces_window.geometry("800x600")
        faces_window.transient(self.root)
        faces_window.grab_set()
        
        # Frame principal
        main_frame = ttk.Frame(faces_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Información superior
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text=f"Total de caras detectadas: {len(self.detected_faces)}", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        # Lista de caras
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('ID', 'Imagen', 'Confianza', 'Coordenadas')
        faces_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=20)
        
        # Configurar columnas
        faces_tree.heading('#0', text='#')
        faces_tree.column('#0', width=50)
        for col in columns:
            faces_tree.heading(col, text=col)
            if col == 'ID':
                faces_tree.column(col, width=60)
            elif col == 'Imagen':
                faces_tree.column(col, width=200)
            elif col == 'Confianza':
                faces_tree.column(col, width=100)
            else:
                faces_tree.column(col, width=200)
        
        # Scrollbar para la lista
        faces_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=faces_tree.yview)
        faces_tree.configure(yscrollcommand=faces_scrollbar.set)
        
        faces_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        faces_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Poblar lista con caras detectadas
        for i, face in enumerate(self.detected_faces, 1):
            bbox = face['bounding_box']
            coordinates = f"x:{bbox.get('x', 0):.0f}, y:{bbox.get('y', 0):.0f}, w:{bbox.get('width', 0):.0f}, h:{bbox.get('height', 0):.0f}"
            
            faces_tree.insert('', 'end', text=str(i), values=(
                f"FACE_{i:03d}",
                face['image_name'],
                f"{face['confidence']:.2f}%",
                coordinates
            ))
        
        # Botones de acción
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Exportar Lista JSON", 
                  command=lambda: self.export_faces_list()).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Copiar al Portapapeles", 
                  command=lambda: self.copy_faces_to_clipboard()).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Ver Detalle", 
                  command=lambda: self.show_face_details(faces_tree)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Cerrar", 
                  command=faces_window.destroy).pack(side=tk.RIGHT)
        
        # Estadísticas adicionales
        stats_frame = ttk.LabelFrame(main_frame, text="Estadísticas", padding="5")
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Calcular estadísticas
        confidences = [face['confidence'] for face in self.detected_faces]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        max_confidence = max(confidences) if confidences else 0
        min_confidence = min(confidences) if confidences else 0
        
        images_with_faces = len(set(face['image_path'] for face in self.detected_faces))
        avg_faces_per_image = len(self.detected_faces) / images_with_faces if images_with_faces else 0
        
        stats_text = f"""Confianza promedio: {avg_confidence:.1f}% | Máxima: {max_confidence:.1f}% | Mínima: {min_confidence:.1f}%
Imágenes con rostros: {images_with_faces} | Promedio por imagen: {avg_faces_per_image:.1f} rostros"""
        
        ttk.Label(stats_frame, text=stats_text, font=('Arial', 9)).pack(anchor=tk.W)
        
    def export_faces_list(self):
        """Exportar lista de caras a archivo JSON"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Guardar lista de caras detectadas"
            )
            
            if filename:
                export_data = {
                    'total_faces': len(self.detected_faces),
                    'export_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'faces': self.detected_faces
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Éxito", f"Lista exportada exitosamente:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Error exportando lista: {str(e)}")
            
    def copy_faces_to_clipboard(self):
        """Copiar información de caras al portapapeles"""
        try:
            clipboard_text = "LISTA DE CARAS DETECTADAS\n" + "="*50 + "\n\n"
            
            for i, face in enumerate(self.detected_faces, 1):
                bbox = face['bounding_box']
                clipboard_text += f"CARA {i:03d}:\n"
                clipboard_text += f"  Imagen: {face['image_name']}\n"
                clipboard_text += f"  Confianza: {face['confidence']:.2f}%\n"
                clipboard_text += f"  Coordenadas: x:{bbox.get('x', 0):.0f}, y:{bbox.get('y', 0):.0f}, w:{bbox.get('width', 0):.0f}, h:{bbox.get('height', 0):.0f}\n\n"
            
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            
            messagebox.showinfo("Copiado", f"Información de {len(self.detected_faces)} caras copiada al portapapeles")
        except Exception as e:
            messagebox.showerror("Error", f"Error copiando al portapapeles: {str(e)}")
            
    def show_face_details(self, tree):
        """Mostrar detalles de cara seleccionada"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Sin selección", "Por favor selecciona una cara de la lista")
            return
            
        item = tree.item(selection[0])
        face_index = int(item['text']) - 1
        
        if 0 <= face_index < len(self.detected_faces):
            face = self.detected_faces[face_index]
            
            details_window = tk.Toplevel(self.root)
            details_window.title(f"Detalles de Cara #{face_index + 1}")
            details_window.geometry("600x500")
            details_window.transient(self.root)
            
            text_widget = tk.Text(details_window, wrap=tk.WORD, font=('Consolas', 10))
            scrollbar = ttk.Scrollbar(details_window, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            # Mostrar información detallada
            details_text = f"""DETALLES DE CARA #{face_index + 1}
{'='*50}

INFORMACIÓN DE ARCHIVO:
   Imagen: {face['image_name']}
   Ruta: {face['image_path']}

DATOS DE DETECCIÓN:
   Confianza: {face['confidence']:.2f}%
   
COORDENADAS (Bounding Box):
   X: {face['bounding_box'].get('x', 0):.0f} píxeles
   Y: {face['bounding_box'].get('y', 0):.0f} píxeles
   Ancho: {face['bounding_box'].get('width', 0):.0f} píxeles
   Alto: {face['bounding_box'].get('height', 0):.0f} píxeles

PUNTOS DE REFERENCIA (Landmarks):
"""
            
            # Agregar landmarks si están disponibles
            landmarks = face.get('landmarks', {})
            if landmarks:
                for landmark, coords in landmarks.items():
                    if isinstance(coords, dict):
                        details_text += f"   {landmark}: x={coords.get('x', 0):.0f}, y={coords.get('y', 0):.0f}\n"
            else:
                details_text += "   No disponibles\n"
            
            # Agregar atributos si están disponibles
            attributes = face.get('attributes', {})
            if attributes:
                details_text += f"\nATRIBUTOS DETECTADOS:\n"
                for attr, value in attributes.items():
                    details_text += f"   {attr}: {value}\n"
            
            text_widget.insert(tk.END, details_text)
            text_widget.configure(state='disabled')
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
    def generate_detection_summary(self, total, successful, total_faces):
        """Generar resumen de detección"""
        success_rate = (successful / total * 100) if total > 0 else 0
        avg_faces = (total_faces / successful) if successful > 0 else 0
        
        return f"""RESUMEN DE DETECCIÓN DE ROSTROS
{'='*60}

Estadísticas de Procesamiento:
   • Imágenes analizadas: {total}
   • Análisis exitosos: {successful}
   • Análisis con errores: {total - successful}
   • Tasa de éxito: {success_rate:.1f}%

Resultados de Detección:
   • Total de rostros detectados: {total_faces}
   • Promedio por imagen exitosa: {avg_faces:.1f}
   • Imágenes con rostros: {successful}
   • Imágenes sin rostros: {total - successful}

Información del Proceso:
   • Procesado: {time.strftime('%Y-%m-%d %H:%M:%S')}
   • Proveedor: Amazon Rekognition
   • Velocidad promedio: ~0.5 seg/imagen

Siguiente Paso:
   {'Usa "Agregar Caras a Lista" para gestionar los rostros detectados' if total_faces > 0 else 'Intenta con imágenes que contengan rostros más claros'}

Calidad de Detección:
   {'Excelente detección' if success_rate > 90 else 'Revisa calidad de imágenes' if success_rate < 70 else 'Buena detección'}
"""
        
    def initialize_explorer(self):
        home_path = str(Path.home())
        self.current_folder.set(home_path)
        self.load_folder_tree(home_path)
        
    def load_folder_tree(self, root_path):
        """Cargar árbol de carpetas expandible"""
        try:
            root_path = Path(root_path).expanduser().resolve()
            if not root_path.exists() or not root_path.is_dir():
                return
                
            self.current_folder.set(str(root_path))
            
            # Limpiar árbol
            for item in self.folder_tree.get_children():
                self.folder_tree.delete(item)
                
            # Cargar estructura de árbol
            self.populate_tree_node('', root_path)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando árbol: {str(e)}")
            
    def populate_tree_node(self, parent_item, folder_path):
        """Poblar un nodo del árbol con sus subcarpetas"""
        try:
            items = []
            # Solo agregar carpetas al árbol
            for item in folder_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    items.append(item)
                    
            # Ordenar carpetas
            items.sort(key=lambda x: x.name.lower())
            
            for folder in items:
                # Truncar nombres muy largos
                display_name = folder.name if len(folder.name) <= 35 else folder.name[:32] + "..."
                
                # Verificar si tiene subcarpetas
                has_subdirs = self.has_subdirectories(folder)
                
                # Crear nodo
                node_id = self.folder_tree.insert(parent_item, 'end', 
                                                 text=f"📁 {display_name}", 
                                                 values=(str(folder),),
                                                 open=False)
                
                # Si tiene subcarpetas, agregar placeholder para mostrar el +
                if has_subdirs:
                    self.folder_tree.insert(node_id, 'end', text="Loading...", values=("",))
                    
        except PermissionError:
            if parent_item == '':
                self.folder_tree.insert('', 'end', text="Sin permisos de acceso")
                
    def has_subdirectories(self, folder_path):
        """Verificar si una carpeta tiene subdirectorios"""
        try:
            for item in folder_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    return True
            return False
        except PermissionError:
            return False
            
    def on_folder_select(self, event):
        """Al seleccionar carpeta, mostrar sus imágenes automáticamente"""
        selection = self.folder_tree.selection()
        if selection:
            item = self.folder_tree.item(selection[0])
            if item['values'] and item['values'][0]:
                folder_path = item['values'][0]
                if Path(folder_path).is_dir():
                    # Expandir/contraer nodo si tiene hijos
                    self.expand_or_collapse_node(selection[0])
                    # Cargar imágenes de esta carpeta
                    self.load_images_in_folder(Path(folder_path))
                    
    def expand_or_collapse_node(self, node_id):
        """Expandir o contraer nodo del árbol"""
        if self.folder_tree.item(node_id, 'open'):
            # Si está abierto, cerrarlo
            self.folder_tree.item(node_id, open=False)
        else:
            # Si está cerrado, abrirlo
            children = self.folder_tree.get_children(node_id)
            if children and self.folder_tree.item(children[0], 'text') == "Loading...":
                # Eliminar placeholder y cargar contenido real
                self.folder_tree.delete(children[0])
                folder_path = Path(self.folder_tree.item(node_id, 'values')[0])
                self.populate_tree_node(node_id, folder_path)
            self.folder_tree.item(node_id, open=True)
            
    def load_folder(self, folder_path):
        """Cargar carpeta específica desde la ruta de texto"""
        self.load_folder_tree(folder_path)
            
    def load_images_in_folder(self, folder_path):
        self.image_files.clear()
        self.selected_images.clear()
        self.thumbnails_cache.clear()
        
        # Buscar imágenes
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        for ext in image_extensions:
            self.image_files.extend(list(folder_path.glob(f'*{ext}')))
            self.image_files.extend(list(folder_path.glob(f'*{ext.upper()}')))
            
        # Cargar identificaciones de rostros para esta carpeta
        self.load_face_identifications()
            
        self.update_selection_info()
        self.create_thumbnails()
        
    def create_thumbnails(self):
        # Limpiar miniaturas anteriores
        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()
            
        if not self.image_files:
            ttk.Label(self.thumbnails_frame, text="No hay imágenes en esta carpeta", 
                     font=('Arial', 12)).pack(pady=50)
            return
            
        # Crear grid de miniaturas
        cols = 4  # Número de columnas
        for i, image_path in enumerate(self.image_files):
            row = i // cols
            col = i % cols
            
            self.create_thumbnail_widget(image_path, row, col)
            
        # Actualizar scroll region
        self.thumbnails_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
    def create_thumbnail_widget(self, image_path, row, col):
        # Frame para cada miniatura
        thumb_frame = ttk.Frame(self.thumbnails_frame, relief='solid', borderwidth=1, padding=5)
        thumb_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
        
        try:
            # Crear miniatura
            with Image.open(image_path) as img:
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
            # Guardar referencia
            self.thumbnails_cache[str(image_path)] = photo
            
            # Variable para checkbox
            var = tk.BooleanVar()
            
            # Checkbox
            cb = ttk.Checkbutton(thumb_frame, variable=var, 
                               command=lambda p=image_path, v=var: self.on_image_select(p, v))
            cb.pack(anchor='nw')
            
            # Label con imagen
            img_label = ttk.Label(thumb_frame, image=photo)
            img_label.pack()
            
            # Nombre del archivo
            name_label = ttk.Label(thumb_frame, text=image_path.name, font=('Arial', 8))
            name_label.pack()
            
            # Información del archivo
            size_mb = round(image_path.stat().st_size / (1024*1024), 2)
            info_label = ttk.Label(thumb_frame, text=f"{size_mb} MB", font=('Arial', 7))
            info_label.pack()
            
            # Eventos de clic en la imagen
            img_label.bind('<Button-1>', lambda e, p=image_path, v=var: self.toggle_image_selection(p, v, cb))
            img_label.bind('<Double-Button-1>', lambda e, p=image_path: self.open_image_viewer(p))
            
        except Exception as e:
            # Error cargando imagen
            error_label = ttk.Label(thumb_frame, text=f"Error\n{image_path.name}\nError: {str(e)[:20]}...", 
                                   font=('Arial', 8))
            error_label.pack()
            
    def on_image_select(self, image_path, var):
        if var.get():
            self.selected_images.add(str(image_path))
        else:
            self.selected_images.discard(str(image_path))
        self.update_selection_info()
        
    def toggle_image_selection(self, image_path, var, checkbox):
        var.set(not var.get())
        checkbox.invoke()
        
    def select_all_images(self):
        self.selected_images = {str(path) for path in self.image_files}
        # Actualizar checkboxes
        self.create_thumbnails()
        self.update_selection_info()
        
    def clear_selection(self):
        self.selected_images.clear()
        self.create_thumbnails()
        self.update_selection_info()
        
    def go_home(self):
        self.load_folder_tree(str(Path.home()))
        
    def go_up(self):
        current = Path(self.current_folder.get())
        if current.parent != current:
            self.load_folder_tree(str(current.parent))
            
    def refresh_folder(self):
        self.load_folder_tree(self.current_folder.get())
        
    def on_folder_double_click(self, event):
        """Doble clic en carpeta para navegar"""
        pass
                    
    def on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
    def on_mousewheel(self, event):
        # Compatibilidad multiplataforma para scroll
        if hasattr(event, 'delta'):
            # Windows y macOS
            delta = int(-1 * (event.delta / 120))
        else:
            # Linux
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = 0
        self.canvas.yview_scroll(delta, "units")
        
    def process_single_image(self, image_path):
        try:
            headers = {"Authorization": f"Bearer {self.api_key.get()}"}
            
            with open(image_path, 'rb') as image_file:
                files = {'file': image_file}
                data = {
                    'providers': 'amazon',
                    'fallback_providers': 'amazon'
                }
                
                response = requests.post(
                    "https://api.edenai.run/v2/image/face_detection",
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}: {response.text}"}
                    
        except Exception as e:
            return {"error": f"Error procesando: {str(e)}"}
            
    def add_result_to_table(self, index, filename, faces, confidence, status, size):
        self.details_tree.insert('', 'end', text=str(index), 
                                values=(filename, faces, confidence, status, size))

    def save_results_to_file(self):
        if not self.results_cache:
            return
            
        current_path = Path(self.current_folder.get())
        output_file = current_path / f"eden_ai_results_{int(time.time())}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results_cache, f, indent=2, ensure_ascii=False)
                
            self.status_var.set(f"Resultados guardados: {output_file.name}")
            
            if self.auto_open_results.get():
                try:
                    os.system(f'xdg-open "{output_file}"')  # Linux
                except:
                    try:
                        os.system(f'open "{output_file}"')  # macOS
                    except:
                        try:
                            os.startfile(output_file)  # Windows
                        except:
                            pass  # Si no funciona ninguno, continúa sin abrir
                
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando resultados: {str(e)}")
            
            
    def run(self):
        self.root.mainloop()

    def open_image_viewer(self, image_path):
        """Abrir visor de imagen grande con detección de rostros interactiva"""
        # Crear ventana del visor
        viewer_window = tk.Toplevel(self.root)
        viewer_window.title(f"Visor de Imagen - {Path(image_path).name}")
        viewer_window.geometry("1000x800")
        viewer_window.transient(self.root)
        
        # Variables para el visor
        self.current_image_path = str(image_path)
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Frame principal
        main_frame = ttk.Frame(viewer_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Toolbar superior
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(toolbar_frame, text=f"Imagen: {Path(image_path).name}", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        # Botones de control
        controls_frame = ttk.Frame(toolbar_frame)
        controls_frame.pack(side=tk.RIGHT)
        
        ttk.Button(controls_frame, text="Zoom +", command=lambda: self.zoom_image(viewer_window, 1.2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Zoom -", command=lambda: self.zoom_image(viewer_window, 0.8)).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Ajustar", command=lambda: self.fit_image(viewer_window)).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Detectar Rostros", command=lambda: self.detect_faces_in_viewer(viewer_window)).pack(side=tk.LEFT, padx=5)
        
        # Canvas para la imagen
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.viewer_canvas = tk.Canvas(canvas_frame, bg='gray20', cursor='crosshair')
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.viewer_canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.viewer_canvas.yview)
        
        self.viewer_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.viewer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Info panel lateral
        info_frame = ttk.LabelFrame(main_frame, text="Información de Rostros", width=300)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        info_frame.pack_propagate(False)
        
        self.faces_listbox = tk.Listbox(info_frame, height=15)
        faces_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.faces_listbox.yview)
        self.faces_listbox.configure(yscrollcommand=faces_scroll.set)
        
        self.faces_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        faces_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Controles de identificación
        id_frame = ttk.Frame(info_frame)
        id_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Label(id_frame, text="Identificar rostro:").pack(anchor=tk.W)
        self.name_entry = ttk.Entry(id_frame, width=25)
        self.name_entry.pack(fill=tk.X, pady=2)
        
        ttk.Button(id_frame, text="Asignar Nombre", 
                  command=lambda: self.assign_face_name(viewer_window)).pack(fill=tk.X, pady=2)
        ttk.Button(id_frame, text="Quitar Identificación", 
                  command=lambda: self.remove_face_name(viewer_window)).pack(fill=tk.X, pady=2)
        
        # Eventos del canvas
        self.viewer_canvas.bind('<Button-1>', lambda e: self.on_face_click(e, viewer_window))
        self.viewer_canvas.bind('<B1-Motion>', self.on_pan_drag)
        self.viewer_canvas.bind('<ButtonPress-2>', self.on_pan_start)  # Botón medio
        self.viewer_canvas.bind('<B2-Motion>', self.on_pan_drag)
        
        # Cargar y mostrar imagen
        self.load_image_in_viewer(viewer_window)
        
        # Si ya hay rostros detectados, mostrarlos
        self.update_faces_display(viewer_window)
        
    def load_image_in_viewer(self, viewer_window):
        """Cargar imagen en el visor"""
        try:
            # Cargar imagen original
            self.original_image = Image.open(self.current_image_path)
            self.fit_image(viewer_window)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando imagen: {str(e)}")
            
    def fit_image(self, viewer_window):
        """Ajustar imagen al tamaño del canvas"""
        if not hasattr(self, 'original_image'):
            return
            
        # Obtener dimensiones del canvas
        canvas_width = self.viewer_canvas.winfo_width()
        canvas_height = self.viewer_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            viewer_window.after(100, lambda: self.fit_image(viewer_window))
            return
            
        # Calcular zoom para ajustar
        img_width, img_height = self.original_image.size
        zoom_w = canvas_width / img_width
        zoom_h = canvas_height / img_height
        self.zoom_level = min(zoom_w, zoom_h) * 0.9  # 90% para dejar margen
        
        self.pan_x = 0
        self.pan_y = 0
        self.update_image_display(viewer_window)
        
    def zoom_image(self, viewer_window, factor):
        """Hacer zoom en la imagen"""
        self.zoom_level *= factor
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))  # Limitar zoom
        self.update_image_display(viewer_window)
        
    def update_image_display(self, viewer_window):
        """Actualizar visualización de la imagen con rostros"""
        if not hasattr(self, 'original_image'):
            return
            
        # Redimensionar imagen
        img_width = int(self.original_image.width * self.zoom_level)
        img_height = int(self.original_image.height * self.zoom_level)
        
        display_image = self.original_image.resize((img_width, img_height), Image.Resampling.LANCZOS)
        
        # Convertir a PhotoImage
        self.photo = ImageTk.PhotoImage(display_image)
        
        # Limpiar canvas
        self.viewer_canvas.delete("all")
        
        # Mostrar imagen
        self.image_item = self.viewer_canvas.create_image(
            self.pan_x, self.pan_y, anchor='nw', image=self.photo
        )
        
        # Dibujar rostros detectados
        self.draw_detected_faces()
        
        # Actualizar scroll region
        self.viewer_canvas.configure(scrollregion=self.viewer_canvas.bbox("all"))
        
    def draw_detected_faces(self):
        """Dibujar rectángulos sobre los rostros detectados"""
        image_faces = [face for face in self.detected_faces 
                      if face['image_path'] == self.current_image_path]
        
        for i, face in enumerate(image_faces):
            bbox = face['bounding_box']
            
            # Calcular coordenadas escaladas
            x1 = (bbox.get('x', 0) * self.zoom_level) + self.pan_x
            y1 = (bbox.get('y', 0) * self.zoom_level) + self.pan_y
            x2 = x1 + (bbox.get('width', 0) * self.zoom_level)
            y2 = y1 + (bbox.get('height', 0) * self.zoom_level)
            
            # Color del rectángulo (verde si identificado, rojo si no)
            face_id = face['face_id']
            color = 'lime' if face_id in self.face_identifications else 'red'
            
            # Dibujar rectángulo
            rect_id = self.viewer_canvas.create_rectangle(
                x1, y1, x2, y2, outline=color, width=3, tags=f"face_{i}"
            )
            
            # Etiqueta con nombre o número
            name = self.face_identifications.get(face_id, f"Rostro {i+1}")
            confidence = f"{face['confidence']:.1f}%"
            label_text = f"{name}\n({confidence})"
            
            # Fondo para el texto
            text_bg = self.viewer_canvas.create_rectangle(
                x1, y1-30, x1+len(label_text)*6, y1, fill=color, outline=color, tags=f"face_{i}"
            )
            
            # Texto de identificación
            text_id = self.viewer_canvas.create_text(
                x1+5, y1-15, text=label_text, anchor='w', fill='white',
                font=('Arial', 9, 'bold'), tags=f"face_{i}"
            )
            
            # Asociar elementos con el índice de la cara
            self.viewer_canvas.tag_bind(f"face_{i}", '<Button-1>', 
                                      lambda e, idx=i: self.select_face(idx))
                                      
    def on_face_click(self, event, viewer_window):
        """Manejar clic en rostros"""
        # Encontrar elemento clickeado
        clicked_item = self.viewer_canvas.find_closest(event.x, event.y)[0]
        tags = self.viewer_canvas.gettags(clicked_item)
        
        # Verificar si se clickeó en un rostro
        for tag in tags:
            if tag.startswith('face_'):
                face_index = int(tag.split('_')[1])
                self.select_face(face_index)
                break
                
    def select_face(self, face_index):
        """Seleccionar un rostro para identificación"""
        image_faces = [face for face in self.detected_faces 
                      if face['image_path'] == self.current_image_path]
        
        if 0 <= face_index < len(image_faces):
            self.selected_face_index = face_index
            selected_face = image_faces[face_index]
            
            # Actualizar listbox
            self.faces_listbox.selection_clear(0, tk.END)
            self.faces_listbox.selection_set(face_index)
            
            # Mostrar nombre actual en el campo de entrada
            face_id = selected_face['face_id']
            current_name = self.face_identifications.get(face_id, "")
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, current_name)
            
    def assign_face_name(self, viewer_window):
        """Asignar nombre a rostro seleccionado"""
        if not hasattr(self, 'selected_face_index'):
            messagebox.showwarning("Sin selección", "Por favor selecciona un rostro primero")
            return
            
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Nombre vacío", "Por favor ingresa un nombre")
            return
            
        # Obtener rostro seleccionado
        image_faces = [face for face in self.detected_faces 
                      if face['image_path'] == self.current_image_path]
        
        if self.selected_face_index < len(image_faces):
            selected_face = image_faces[self.selected_face_index]
            face_id = selected_face['face_id']
            
            # Asignar nombre
            self.face_identifications[face_id] = name
            
            # Actualizar visualización
            self.update_image_display(viewer_window)
            self.update_faces_display(viewer_window)
            
            # Guardar identificaciones
            self.save_face_identifications()
            
    def remove_face_name(self, viewer_window):
        """Quitar identificación de rostro seleccionado"""
        if not hasattr(self, 'selected_face_index'):
            messagebox.showwarning("Sin selección", "Por favor selecciona un rostro primero")
            return
            
        image_faces = [face for face in self.detected_faces 
                      if face['image_path'] == self.current_image_path]
        
        if self.selected_face_index < len(image_faces):
            selected_face = image_faces[self.selected_face_index]
            face_id = selected_face['face_id']
            
            # Remover identificación
            if face_id in self.face_identifications:
                del self.face_identifications[face_id]
                
                # Limpiar campo de entrada
                self.name_entry.delete(0, tk.END)
                
                # Actualizar visualización
                self.update_image_display(viewer_window)
                self.update_faces_display(viewer_window)
                
                # Guardar cambios
                self.save_face_identifications()
                
    def update_faces_display(self, viewer_window):
        """Actualizar lista de rostros en el panel lateral"""
        self.faces_listbox.delete(0, tk.END)
        
        image_faces = [face for face in self.detected_faces 
                      if face['image_path'] == self.current_image_path]
        
        for i, face in enumerate(image_faces):
            face_id = face['face_id']
            name = self.face_identifications.get(face_id, "Sin identificar")
            confidence = face['confidence']
            
            display_text = f"Rostro {i+1}: {name} ({confidence:.1f}%)"
            self.faces_listbox.insert(tk.END, display_text)
            
    def detect_faces_in_viewer(self, viewer_window):
        """Detectar rostros en la imagen actual del visor"""
        try:
            # Mostrar progreso
            self.status_var.set("Detectando rostros en imagen...")
            
            # Procesar imagen
            result = self.process_single_image(self.current_image_path)
            
            if 'error' not in result and 'amazon' in result:
                items = result.get('amazon', {}).get('items', [])
                
                # Limpiar rostros anteriores de esta imagen
                self.detected_faces = [face for face in self.detected_faces 
                                     if face['image_path'] != self.current_image_path]
                
                # Agregar nuevos rostros detectados
                for i, face_data in enumerate(items):
                    face_info = {
                        'image_path': self.current_image_path,
                        'image_name': Path(self.current_image_path).name,
                        'confidence': face_data.get('confidence', 0),
                        'bounding_box': face_data.get('bounding_box', {}),
                        'landmarks': face_data.get('landmarks', {}),
                        'attributes': face_data.get('attributes', {}),
                        'face_id': f"{Path(self.current_image_path).name}_{i}"
                    }
                    self.detected_faces.append(face_info)
                
                # Actualizar visualización
                self.update_image_display(viewer_window)
                self.update_faces_display(viewer_window)
                self.update_selection_info()
                
                self.status_var.set(f"Detectados {len(items)} rostros en la imagen")
                
            else:
                error_msg = result.get('error', 'Error desconocido')
                messagebox.showerror("Error", f"Error detectando rostros: {error_msg}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error en detección: {str(e)}")
            
    def on_pan_start(self, event):
        """Iniciar paneo con botón medio"""
        self.last_x = event.x
        self.last_y = event.y
        
    def on_pan_drag(self, event):
        """Arrastrar imagen (paneo)"""
        if hasattr(self, 'last_x') and hasattr(self, 'last_y'):
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            self.pan_x += dx
            self.pan_y += dy
            
            self.viewer_canvas.move(self.image_item, dx, dy)
            self.viewer_canvas.move("face", dx, dy)  # Mover también los rostros
            
            self.last_x = event.x
            self.last_y = event.y
            
    def save_face_identifications(self):
        """Guardar identificaciones de rostros en archivo JSON"""
        try:
            current_path = Path(self.current_folder.get())
            identifications_file = current_path / "face_identifications.json"
            
            with open(identifications_file, 'w', encoding='utf-8') as f:
                json.dump(self.face_identifications, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error guardando identificaciones: {e}")
            
    def load_face_identifications(self):
        """Cargar identificaciones de rostros desde archivo JSON"""
        try:
            current_path = Path(self.current_folder.get())
            identifications_file = current_path / "face_identifications.json"
            
            if identifications_file.exists():
                with open(identifications_file, 'r', encoding='utf-8') as f:
                    self.face_identifications = json.load(f)
                    
        except Exception as e:
            print(f"Error cargando identificaciones: {e}")
            self.face_identifications = {}

if __name__ == "__main__":
    try:
        app = AdvancedEdenAIGUI()
        app.run()
    except ImportError as e:
        print("Error: Falta instalar dependencias.")
        print("Ejecuta: pip install pillow requests")
        print(f"Error específico: {e}")
